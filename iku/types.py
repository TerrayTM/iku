from typing import Dict, List, NamedTuple, Optional

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
    size_discovered: int
    size_written: int
    size_skipped: int
    current_relative_path: Optional[str]


class SynchronizationResult(NamedTuple):
    files_indexed: int
    total_files: int
    details: SynchronizationDetails
    index_diff_report: Dict[str, List[str]]
    sync_diff_report: Dict[str, List[str]]
