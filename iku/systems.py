import hashlib
import os
from contextlib import contextmanager
from ctypes import WinError
from pathlib import Path
from typing import ContextManager, Iterator, List, Optional, Tuple

from paramiko.client import SSHClient

from iku.config import Config
from iku.tools import write_ctime
from iku.types import FileInfo


class FileSystem:
    def __init__(self, base_folder: str) -> None:
        self._base_folder = base_folder

    def isfile(self, path: str) -> bool:
        return os.path.isfile(path)

    def rename(self, src: str, dst: str) -> None:
        os.rename(src, dst)

    def unlink(self, path: str) -> None:
        os.unlink(path)

    def getmtime(self, path: str) -> float:
        return os.path.getmtime(path)

    def getsize(self, path: str) -> int:
        return os.path.getsize(path)

    def join(self, path: str, *paths: str) -> str:
        return os.path.join(path, *paths)

    def rglob_files(self) -> Iterator[str]:
        return iter(
            str(file) for file in Path(self._base_folder).rglob("*") if file.is_file()
        )

    def relpath(self, path: str, start: str) -> str:
        return os.path.relpath(path, start)

    def md5_hash(self, path: str) -> str:
        """
        Computes the MD5 hash of a given file.

        Parameters
        ----------
        path : str
            The absolute path of the file.

        Returns
        -------
        result : str
            The MD5 hash of the file.
        """
        file_hash = hashlib.md5()

        with open(path, "rb") as file:
            while True:
                data = file.read(Config.buffer_size)

                if not data:
                    break

                file_hash.update(data)

        return file_hash.hexdigest()

    def utime(self, path: str, times: Tuple[float, float]) -> None:
        os.utime(path, times)

    def ctime(self, path: str, time: Optional[float]) -> None:
        if time is None:
            return

        try:
            write_ctime(path, time)
        except WinError:
            pass  # check this

    def stat(self, path: str) -> FileInfo:
        raise NotImplementedError()

    def dirname(self, path: str) -> str:
        return os.path.dirname(path)

    def mkdir(self, folder_path: str) -> None:
        Path(folder_path).mkdir(parents=True, exist_ok=True)

    def remove_empty_folders(self, base_folder: str) -> None:
        for dirpath, dirs, files in os.walk(base_folder):
            if not dirs and not files:
                os.rmdir(dirpath)

    def open(self, path: str, mode: str) -> ContextManager:
        return open(path, mode)

    def close(self):
        pass


class RemoteFileSystem(FileSystem):
    def __init__(
        self,
        base_folder: str,
        hostname: str,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self._client = SSHClient()
        self._client.load_system_host_keys()
        self._client.connect(hostname, port, username, password)
        self._stfp = self._client.open_sftp()
        real_path = f"$(realpath {base_folder})"
        self._cache = None

        output = self._exec_command(f"[ -d {real_path} ] && echo {real_path}")
        if not output:
            raise FileNotFoundError()

        self._base_folder = output[0].strip()

    def _exec_command(self, command: str) -> List[str]:
        stdout = self._client.exec_command(command)[1]
        stdout.channel.recv_exit_status()
        return stdout.readlines()

    def _update_cache(self, target_path: str):
        for line in self._exec_command(
            f"find {target_path} -type f -printf '%p|%s|%T@|%A@\\n'"
        ):
            path, size, last_modified, last_accessed = line.split("|")
            self._cache[path] = FileInfo(
                os.path.basename(path),
                int(size),
                float(last_modified),
                None,
                float(last_accessed),
            )

    def _build_cache_if_needed(self):
        if self._cache is None:
            self._cache = {}
            self._update_cache(self._base_folder)

    def isfile(self, path: str) -> bool:
        self._build_cache_if_needed()
        return path in self._cache

    def rename(self, src: str, dst: str):
        if not self.isfile(src) or self.isfile(dst):
            raise ValueError()

        self._stfp.rename(src, dst)
        self._cache[dst] = self._cache[src]
        self._cache.pop(src)

    def unlink(self, path: str) -> None:
        if not self.isfile(path):
            raise ValueError()

        self._stfp.unlink(path)
        self._cache.pop(path)

    def getmtime(self, path: str) -> float:
        if not self.isfile(path):
            raise ValueError()

        return self._cache[path].last_modified

    def getsize(self, path: str) -> int:
        if not self.isfile(path):
            raise ValueError()

        return self._cache[path].size

    def join(self, path: str, *paths: str) -> str:
        return os.path.join(path, *paths).replace(os.sep, "/")

    def rglob_files(self) -> Iterator[str]:
        self._build_cache_if_needed()

        return iter(self._cache.keys())

    def relpath(self, path: str, start: str) -> str:
        return os.path.relpath(path, start)

    def md5_hash(self, path: str) -> str:
        if not self.isfile(path):
            raise ValueError()

        output = self._exec_command(f"md5sum {path}")
        return output[0].split()[0]

    def utime(self, path: str, times: Tuple[float, float]) -> None:
        if not self.isfile(path):
            raise FileNotFoundError()

        self._stfp.utime(path, times)

    def ctime(self, path: str, time: Optional[float]) -> None:
        pass

    def stat(self, path: str) -> FileInfo:
        if not self.isfile(path):
            raise FileNotFoundError()

        return self._cache[path]

    def mkdir(self, folder_path: str) -> None:
        self._exec_command(f"mkdir -p {folder_path}")

    def remove_empty_folders(self, base_folder: str) -> None:
        """find test -depth -type d -empty -delete"""

    def open(self, path: str, mode: str) -> ContextManager:
        self._build_cache_if_needed()
        file = self._stfp.open(path, mode)

        if "w" in mode:
            close = file.close
            file.close = lambda: None if self._update_cache(path) or close() else None

        return file

    def close(self) -> None:
        self._stfp.close()
        self._client.close()

    @property
    def base_folder(self) -> str:
        return self._base_folder
