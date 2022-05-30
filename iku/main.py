import argparse
import time

from tabulate import tabulate

from iku.config import Config
from iku.console import format_cyan, format_green, format_red, output
from iku.constants import (DIFF_ADDED, DIFF_MODIFIED, DIFF_REMOVED, RC_FAILED,
                           RC_INTERRUPTED, RC_INVALID_ARGUMENT,
                           RC_MISSING_INFO, RC_NO_DEVICE_FOUND,
                           RC_NO_DEVICE_WITH_NAME, RC_OK)
from iku.core import synchronize_to_folder
from iku.driver import bind_iphone_drivers
from iku.exceptions import KeyboardInterruptWithDataException
from iku.info import IKU_INFO
from iku.parser import parse_args
from iku.tools import format_file_size
from iku.types import SynchronizationResult
from iku.version import __version__


def _print_sync_result(result: SynchronizationResult, success: bool):
    details = result.details
    index_progress = 50
    if result.total_indices > 0:
        index_progress = result.files_indexed / result.total_indices * 50

    sync_progress = 50
    if result.total_files > 0:
        sync_progress = (
            (details.files_copied + details.files_skipped) / result.total_files * 50
        )

    progress = f"{round(index_progress + sync_progress, 2)}%"
    table = tabulate(
        [
            ["Files Indexed", format_cyan(result.files_indexed)],
            ["Files on Device", format_cyan(result.total_files)],
            ["Files Copied", format_cyan(details.files_copied)],
            ["Files Skipped", format_cyan(details.files_skipped)],
            [
                "Size Discovered",
                format_cyan(format_file_size(details.size_discovered)),
            ],
            [
                "Size Copied",  # size copied
                format_cyan(format_file_size(details.size_copied)),
            ],
            ["Size Skipped", format_cyan(format_file_size(details.size_skipped)),],
            ["Progress", format_cyan(progress) if success else format_red(progress),],
        ],
        tablefmt="pretty",
        colalign=("left", "right"),
    )
    table_width = len(table.split("\n")[0])

    output(f"+{'-' * (table_width - 2)}+")
    output(f"| Summary{' ' * (table_width - 10)}|")
    output(table)
    output(
        tabulate(
            [
                ["Added", format_cyan(len(result.sync_diff[DIFF_ADDED])),],
                ["Modified", format_cyan(len(result.sync_diff[DIFF_MODIFIED])),],
                ["Removed", format_cyan(len(result.sync_diff[DIFF_REMOVED])),],
            ],
            headers=("Difference", "Files"),
            tablefmt="pretty",
            colalign=("left", "right"),
        )
    )

    if details.current_destination_path is not None:
        output(f"Error copying file to {details.current_destination_path}")
        output("Try replugging in your device and running sync again,")


def _print_status(rc: int, start_time: float):
    if rc == RC_OK:
        status = format_green("[OK]")
    elif rc == RC_INTERRUPTED:
        status = format_red("[INTERRUPTED]")
    elif rc == RC_FAILED:
        status = format_red("[FAILED]")
    else:
        return

    total_seconds = round(time.time() - start_time, 2)
    output(f"{status} Elapsed time: {format_cyan(f'{total_seconds}s')}")


def _execute_discover_command(args: argparse.Namespace) -> int:
    drivers = bind_iphone_drivers()

    output(
        tabulate(
            [[driver.name, driver.type] for driver in drivers],
            headers=["Name", "Type"],
            tablefmt="pretty",
        )
    )

    return RC_OK


def _execute_sync_command(args: argparse.Namespace) -> int:
    Config.silent = args.silent
    Config.destructive = args.destructive
    Config.delay = args.delay
    Config.retries = args.retries
    Config.buffer_size = args.buffer_size

    drivers = bind_iphone_drivers()

    if len(drivers) == 0:
        output("No devices were detected on computer.")
        return RC_NO_DEVICE_FOUND

    selected_driver = drivers[0]

    if args.device_name is not None:
        selected_driver = next(
            (driver for driver in drivers if driver.name == args.device_name), None
        )

        if selected_driver is None:
            output(f'Device with name "{args.device_name}" is not found.')
            output(f"Please choose one from the following list of device names:")

            for driver in drivers:
                output(f"- {driver.name}")

            return RC_NO_DEVICE_WITH_NAME
    elif len(drivers) > 1:
        output("Found multiple devices:")
        for driver in drivers:
            output(f"- {driver.name}")

        output("Please specify which device to sync from using --device-name argument.")

        return RC_MISSING_INFO

    try:
        rc = RC_OK
        result = synchronize_to_folder(selected_driver, args.folder)
    except KeyboardInterruptWithDataException as exception:
        rc = RC_INTERRUPTED
        result = exception.data
    except KeyboardInterrupt:
        return RC_INTERRUPTED

    if result.details.current_destination_path is not None:
        rc = RC_FAILED

    if args.index_diff_path is not None:
        with open(args.index_diff_path, "w") as file:
            file.write(str(result.index_diff))

    if args.sync_diff_path is not None:
        with open(args.sync_diff_path, "w") as file:
            file.write(str(result.sync_diff))

    _print_sync_result(result, rc == RC_OK)

    return rc


def main() -> int:
    args = parse_args()

    if args is None:
        return RC_INVALID_ARGUMENT

    if args.show_version:
        output(__version__)
        return RC_OK

    if args.show_info:
        output(IKU_INFO)
        return RC_OK

    rc = RC_OK
    start_time = time.time()

    if args.command == "discover":
        rc = _execute_discover_command(args)
    elif args.command == "sync":
        rc = _execute_sync_command(args)

    _print_status(rc, start_time)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
