from typing import Iterable, List, Optional

from pywintypes import com_error
from win32com.shell import shell, shellcon

from iku.constants import (
    DCIM_NAME,
    DEVICE_IPHONE,
    INTERNAL_STORAGE_NAME,
    PC_DISPLAY_NAMES,
)
from iku.file import DeviceFile
from iku.types import DeviceInfo, PyIShellFolder


class iPhoneDriver:
    def __init__(self, device_info: DeviceInfo) -> None:
        self._name = device_info.device_name
        self._dcim_folder = device_info.dcim_parent.BindToObject(
            device_info.dcim_pidl, None, shell.IID_IShellFolder
        )

    def list_files(self) -> Iterable[DeviceFile]:
        for folder_pidl in self._dcim_folder.EnumObjects(0, shellcon.SHCONTF_FOLDERS):
            folder_name = self._dcim_folder.GetDisplayNameOf(
                folder_pidl, shellcon.SHGDN_NORMAL
            )
            folder = self._dcim_folder.BindToObject(
                folder_pidl, None, shell.IID_IShellFolder
            )
            for pidl in folder.EnumObjects(0, shellcon.SHCONTF_NONFOLDERS):
                yield DeviceFile(pidl, folder, folder_name)

    def count_files(self) -> int:
        count = 0
        for folder_pidl in self._dcim_folder.EnumObjects(0, shellcon.SHCONTF_FOLDERS):
            folder = self._dcim_folder.BindToObject(
                folder_pidl, None, shell.IID_IShellFolder
            )
            count += len(list(folder.EnumObjects(0, shellcon.SHCONTF_NONFOLDERS)))
        return count

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return DEVICE_IPHONE


def _get_pc_folder() -> Optional[PyIShellFolder]:
    desktop = shell.SHGetDesktopFolder()
    for pidl in desktop.EnumObjects(0, shellcon.SHCONTF_FOLDERS):
        display_name = desktop.GetDisplayNameOf(pidl, shellcon.SHGDN_NORMAL)
        if display_name in PC_DISPLAY_NAMES:
            return desktop.BindToObject(pidl, None, shell.IID_IShellFolder)
    return None


def _get_dcim_device_info(device_pidl, parent) -> Optional[DeviceInfo]:
    device_name = parent.GetDisplayNameOf(device_pidl, shellcon.SHGDN_NORMAL)
    folder = parent.BindToObject(device_pidl, None, shell.IID_IShellFolder)
    top_pidl = None
    top_dir_name = None
    try:
        for pidl in folder.EnumObjects(0, shellcon.SHCONTF_FOLDERS):
            top_dir_name = folder.GetDisplayNameOf(pidl, shellcon.SHGDN_NORMAL)
            top_pidl = pidl
            break
        if top_dir_name != INTERNAL_STORAGE_NAME:
            return None
    except com_error:
        return None
    internal = folder.BindToObject(top_pidl, None, shell.IID_IShellFolder)
    dcim_candidate = None
    dcim_pidl = None
    for pidl in internal.EnumObjects(0, shellcon.SHCONTF_FOLDERS):
        dcim_candidate = internal.GetDisplayNameOf(pidl, shellcon.SHGDN_NORMAL)
        dcim_pidl = pidl
        break
    if dcim_candidate != DCIM_NAME:
        return None
    return DeviceInfo(dcim_pidl, internal, device_name)


def bind_iphone_drivers() -> List[iPhoneDriver]:
    pc_folder = _get_pc_folder()
    if pc_folder is None:
        return []
    return [
        iPhoneDriver(info)
        for info in filter(
            None, (_get_dcim_device_info(pidl, pc_folder) for pidl in pc_folder)
        )
    ]
