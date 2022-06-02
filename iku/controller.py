import argparse
import os
from typing import Optional, Tuple

from iku.console import clear_last_output, output
from iku.constants import (DEVICE_IPHONE, FILE_SYSTEM_LOCAL,
                           FILE_SYSTEM_REMOTE, FILE_SYSTEM_TYPES,
                           RC_INVALID_ARGUMENT, RC_MISSING_INFO,
                           RC_NO_DEVICE_FOUND, RC_NO_DEVICE_WITH_NAME, RC_OK)
from iku.driver import bind_iphone_drivers, iPhoneDriver
from iku.provider import Provider
from iku.systems import FileSystem, RemoteFileSystem


def _get_iphone_driver(
    device_name: Optional[str],
) -> Tuple[Optional[iPhoneDriver], int]:
    drivers = bind_iphone_drivers()

    if len(drivers) == 0:
        output("No devices were detected on computer.")
        return None, RC_NO_DEVICE_FOUND

    selected_driver = drivers[0]

    if device_name is not None:
        selected_driver = next(
            (driver for driver in drivers if driver.name == device_name), None
        )

        if selected_driver is None:
            output(f'Device with name "{device_name}" is not found.')
            output(f"Please choose one from the following list of device names:")

            for driver in drivers:
                output(f"- {driver.name}")

            return None, RC_NO_DEVICE_WITH_NAME
    elif len(drivers) > 1:
        output("Found multiple devices:")
        for driver in drivers:
            output(f"- {driver.name}")

        output("Please specify which device to sync from using --device-name argument.")

        return None, RC_MISSING_INFO

    return selected_driver, RC_OK


def _get_file_system(base_folder: str) -> Tuple[Optional[FileSystem], int]:
    if not os.path.isdir(base_folder):
        output("Invalid folder path")
        return None, RC_INVALID_ARGUMENT

    return FileSystem(base_folder), RC_OK


def _get_remote_file_system(
    base_folder: str, hostname: str, port: int, username: str, password: str
) -> Tuple[Optional[RemoteFileSystem], int]:
    try:
        fs = RemoteFileSystem(base_folder, hostname, port, username, password)
    except FileNotFoundError:
        output("Invalid folder path")
        return None, RC_INVALID_ARGUMENT
    except:
        pass  # SSH EXCEPTIONS

    return fs, RC_OK


# typing needs to be fixed
def _get_controller(
    args: argparse.Namespace, controller_type: str
) -> Tuple[Optional[FileSystem], int]:
    rc = RC_OK
    controller = None
    folder_type = f"{controller_type}_type"
    path_type = f"{controller_type}_folder"
    controller_name = getattr(args, folder_type)
    base_folder = getattr(args, path_type)

    if controller_name == DEVICE_IPHONE:
        controller, rc = _get_iphone_driver(args.device_name)
    elif controller_name == FILE_SYSTEM_LOCAL:
        controller, rc = _get_file_system(base_folder)
        rc == RC_OK and setattr(args, folder_type, os.path.abspath(base_folder))
    elif controller_name == FILE_SYSTEM_REMOTE:
        output("Connecting to remote host...")

        controller, rc = _get_remote_file_system(
            base_folder, args.hostname, args.port, args.username, args.password
        )

        rc == RC_OK and setattr(args, folder_type, controller.base_folder)
        clear_last_output()

    return controller, rc


def get_provider(args: argparse.Namespace) -> Tuple[Optional[Provider], int]:
    controller, rc = _get_controller(args, "source")

    if rc == RC_OK and args.source_type in FILE_SYSTEM_TYPES:
        controller = Provider(controller, args.source_folder)

    return controller, rc


def get_consumer(args: argparse.Namespace) -> Tuple[Optional[FileSystem], int]:
    return _get_controller(args, "destination")
