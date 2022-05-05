import time
from tabulate import tabulate

from iku.config import Config
from iku.console import format_cyan, format_green, format_red, printMessage
from iku.constants import RC_FAILED, RC_INTERRUPTED, RC_INVALID_ARGUMENT, RC_MISSING_INFO, RC_NO_DEVICE, RC_OK
from iku.exceptions import KeyboardInterruptWithDataException
from iku.info import IKU_INFO
from iku.core import synchronize_to_folder
from iku.driver import bind_iphone_drivers
from iku.parser import parse_args
from iku.tools import format_file_size
from iku.version import __version__

# progress report
# exception handling
# parallism
# other drivers?


def main() -> int:
    args = parse_args()

    if args is None:
        return RC_INVALID_ARGUMENT

    if args.show_version:
        printMessage(__version__)
        return RC_OK

    if args.show_info:
        printMessage(IKU_INFO)
        return RC_OK

    rc = RC_OK
    status = format_green("[OK]")
    drivers = bind_iphone_drivers()
    start_time = time.time()

    if args.command == "discover":
        table = tabulate(
            [[driver.name, driver.type] for driver in drivers],
            headers=["Name", "Type"],
            tablefmt="pretty",
        )
        printMessage(table)
    elif args.command == "sync":

        Config.silent = args.silent
        Config.destructive = args.destructive

        if len(drivers) == 0:
            printMessage("No devices were detected on computer.")
            return RC_NO_DEVICE

        selected_driver = drivers[0]
        if len(drivers) > 1:
            if args.device_name is None:
                printMessage("Found multiple devices:")
                for driver in drivers:
                    printMessage(f"- {driver.name}")
                printMessage(
                    "Please specify which device to sync from using --device-name argument."
                )
                return 1

            for driver in drivers:
                if driver.name == args.device_name:
                    selected_driver = driver
            else:
                printMessage(f'Device with name "{args.device_name}" is not found.')
                printMessage(
                    f"Please choose one from the following list of device names:"
                )
                for driver in drivers:
                    printMessage(f"- {driver.name}")
                return RC_MISSING_INFO

        try:
            result = synchronize_to_folder(selected_driver, args.folder)
        except KeyboardInterruptWithDataException as exception:
            rc = RC_INTERRUPTED
            result = exception.data

        details = result.details

        if details.current_relative_path is not None:
            rc = RC_FAILED

        progress = f"{round((details.files_written + details.files_skipped) / result.total_files * 100, 2)}%"
        table = tabulate(
            [
                ["Files Indexed", format_cyan(result.files_indexed)],
                ["Files on Device", format_cyan(result.total_files)],
                ["Files Written", format_cyan(details.files_written)],
                ["Files Skipped", format_cyan(details.files_skipped)],
                [
                    "Size Discovered",
                    format_cyan(format_file_size(details.size_discovered)),
                ],
                [
                    "Size Written",
                    format_cyan(format_file_size(details.size_written)),
                ],
                [
                    "Size Skipped",
                    format_cyan(format_file_size(details.size_skipped)),
                ],
                [
                    "Progress",
                    format_cyan(progress) if not rc else format_red(progress),
                ],
            ],
            tablefmt="pretty",
            colalign=("left", "right"),
        )
        table_width = len(table.split("\n")[0])

        status = format_green("[OK]") if not rc else format_red("[INTERRUPTED]")
        printMessage(f"+{'-' * (table_width - 2)}+")
        printMessage(f"| Summary{' ' * (table_width - 10)}|")
        printMessage(table)

    total_seconds = round(time.time() - start_time, 2)
    printMessage(f"{status} Elapsed time: {format_cyan(f'{total_seconds}s')}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
