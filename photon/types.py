from typing import List, NamedTuple, Optional

from pywintypes import IIDType, TimeType
from win32com.shell import shell

PyIShellFolder = type(shell.SHGetDesktopFolder())
PIDL = List[bytes]


class IndexRow(NamedTuple):
    file_hash: str
    last_modified: float
    size: int


class StagedIndexData(NamedTuple):
    path: str
    relative_path: str
    backup_path: str
    index_row: Optional[IndexRow]


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


class SynchronizationDetails(NamedTuple):
    files_written: int
    files_skipped: int
    total_size: int
    size_written: int
    size_skipped: int


class SynchronizationResult(NamedTuple):
    success: bool
    details: Optional[SynchronizationDetails]
