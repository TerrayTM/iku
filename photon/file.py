import os
from typing import Iterator

import pythoncom
from photon.exceptions import DeviceFileReadException
from photon.constants import BUFFER_SIZE
from photon.types import PIDL, FileInfo, PyIShellFolder


class DeviceFile:
    def __init__(self, pidl: PIDL, parent: PyIShellFolder, parent_name: str) -> None:
        self._stream = parent.BindToStorage(pidl, None, pythoncom.IID_IStream)
        self._file_info = FileInfo(*self._stream.Stat())
        self._relative_path = os.path.join(parent_name, self._file_info.name)

    def reset_seek(self) -> None:
        self._stream.Seek(0, 0)

    def read(self) -> Iterator[bytes]:
        try:
            yield self._stream.Read(BUFFER_SIZE)
        except:
            raise DeviceFileReadException()

    @property
    def relative_path(self) -> str:
        return self._relative_path

    @property
    def name(self) -> str:
        return self._file_info.name

    @property
    def size(self) -> int:
        return self._file_info.size

    @property
    def last_modified(self) -> float:
        return self._file_info.last_modified.timestamp()

    @property
    def created_time(self) -> float:
        return self._file_info.created_time.timestamp()

    @property
    def last_accessed(self) -> float:
        return self._file_info.last_accessed.timestamp()
