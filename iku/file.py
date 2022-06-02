import os
from typing import Iterator

from pythoncom import IID_IStream
from pywintypes import com_error

from iku.config import Config
from iku.exceptions import FileReadException, FileSeekException
from iku.systems import FileSystem
from iku.types import PIDL, DeviceFileInfo, PyIShellFolder


class File:
    def __init__(self, fs: FileSystem, path: str, relative_path: str) -> None:
        self._fs = fs
        self._path = path
        self._relative_path = relative_path
        self._handle = self._fs.open(self._path, "rb")
        self._file_info = self._fs.stat(self._path)

    def reset_seek(self) -> None:
        """
        Resets the seek of the file read stream to 0.
        """
        try:
            self._handle.seek(0)
        except:
            raise FileSeekException()

    def reopen(self) -> bool:
        """
        Attempts to reopen the file stream for reading.

        Returns
        -------
        result : bool
            Whether the operation succeeded or not.
        """
        try:
            self.close()
            self._handle = self._fs.open(self._path, "rb")
            self._file_info = self._fs.stat(self._path)
        except IOError:
            return False

        return True

    def read(self) -> Iterator[bytes]:
        """
        Reads the file.

        Returns
        -------
        result : Iterator[bytes]
            An iterator of the file stream when read in bytes.
        """
        try:
            while True:
                chunk = self._handle.read(Config.buffer_size)

                if not chunk:
                    break

                yield chunk
        except:
            raise FileReadException()

    def close(self) -> None:
        self._handle.close()

    @property
    def relative_path(self) -> str:
        """
        Gets the relative path of the file.

        Returns
        -------
        result : str
            The relative path of the file.
        """
        return self._relative_path

    @property
    def name(self) -> str:
        """
        Gets the name of the file.

        Returns
        -------
        result : str
            The name of the file.
        """
        return self._file_info.name

    @property
    def size(self) -> int:
        """
        Gets the size of the file.

        Returns
        -------
        result : int
            The size of the file in bytes.
        """
        return self._file_info.size

    @property
    def last_modified(self) -> float:
        """
        Gets the timestamp of when the file was last modified.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.last_modified

    @property
    def created_time(self) -> float:
        """
        Gets the timestamp of when the file was created.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.created_time

    @property
    def last_accessed(self) -> float:
        """
        Gets the timestamp of when the file was last accessed.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.last_accessed


class DeviceFile(File):
    def __init__(self, pidl: PIDL, parent: PyIShellFolder, parent_name: str) -> None:
        """
        Represents a file on a device and provides utilities for reading the file in
        chunks. A file read stream will be opened automatically upon construction.

        Parameters
        ----------
        pidl : PIDL
            The file PIDL.

        parent : PyIShellFolder
            The parent folder of the file.

        parent_name : str
            The name of the parent folder of the file.
        """
        self._pidl = pidl
        self._parent = parent

        if not self._open():
            raise IOError()

        self._relative_path = os.path.join(parent_name, self._file_info.name)

    def _open(self) -> bool:
        try:
            self._stream = self._parent.BindToStorage(self._pidl, None, IID_IStream)
            self._file_info = DeviceFileInfo(*self._stream.Stat())
        except com_error:
            return False
        return True

    def reset_seek(self) -> None:
        """
        Resets the seek of the file read stream to 0.
        """
        try:
            self._stream.Seek(0, 0)
        except com_error:
            raise FileSeekException()

    def reopen(self) -> bool:
        """
        Attempts to reopen the file stream for reading.

        Returns
        -------
        result : bool
            Whether the operation succeeded or not.
        """
        return self._open()

    def read(self) -> Iterator[bytes]:
        """
        Reads the file.

        Returns
        -------
        result : Iterator[bytes]
            An iterator of the file stream when read in bytes.
        """
        try:
            while True:
                chunk = self._stream.Read(Config.buffer_size)

                if not chunk:
                    break

                yield chunk
        except com_error:
            raise FileReadException()

    def close(self):
        pass

    @property
    def relative_path(self) -> str:
        """
        Gets the relative path of the file.

        Returns
        -------
        result : str
            The relative path of the file.
        """
        return self._relative_path

    @property
    def name(self) -> str:
        """
        Gets the name of the file.

        Returns
        -------
        result : str
            The name of the file.
        """
        return self._file_info.name

    @property
    def size(self) -> int:
        """
        Gets the size of the file.

        Returns
        -------
        result : int
            The size of the file in bytes.
        """
        return self._file_info.size

    @property
    def last_modified(self) -> float:
        """
        Gets the timestamp of when the file was last modified.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.last_modified.timestamp()

    @property
    def created_time(self) -> float:
        """
        Gets the timestamp of when the file was created.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.created_time.timestamp()

    @property
    def last_accessed(self) -> float:
        """
        Gets the timestamp of when the file was last accessed.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.last_accessed.timestamp()
