from typing import Iterable

import pythoncom
from win32com.shell import shellcon

from photon.constants import BUFFER_SIZE, DCIM_NAME
from photon.types import PIDL, FileInfo, PyIShellFolder


class DeviceFile:
    def __init__(self, pidl: PIDL, parent: PyIShellFolder) -> None:
        self._stream = parent.BindToStorage(pidl, None, pythoncom.IID_IStream)
        self._file_info = FileInfo(*self._stream.Stat())
        full_path = parent.GetDisplayNameOf(pidl, shellcon.SHGDN_FORADDRESSBAR)
        path_parts = full_path.split("\\")
        self._path = "\\".join(path_parts[path_parts.index(DCIM_NAME) + 1 :])

    def read(self) -> Iterable[bytes]:
        yield self._stream.Read(BUFFER_SIZE)

    @property
    def path(self) -> str:
        return self._path

    @property
    def name(self) -> str:
        return self._file_info.name

    @property
    def size(self) -> int:
        return self._file_info.size

    @property
    def last_modified(self) -> float:
        return self._file_info.last_modified.timestamp()
