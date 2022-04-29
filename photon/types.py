from typing import List, NamedTuple

from pywintypes import IIDType, TimeType
from win32com.shell import shell

PyIShellFolder = type(shell.SHGetDesktopFolder())
PIDL = List[bytes]


class IndexRow(NamedTuple):
    file_hash: str
    last_modified: float
    size: int


class DeviceInfo(NamedTuple):
    dcim_pidl: PIDL
    dcim_parent: PyIShellFolder
    device_name: str


class FileInfo(NamedTuple):
    name: str
    storage_type: int
    size: int
    last_modified: TimeType
    created_time: TimeType
    last_accessed: TimeType
    mode: int
    locks_supported: int
    identifier: IIDType
    state_bits: int
    storage_format: int
