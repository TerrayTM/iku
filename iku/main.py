import time
from tabulate import tabulate

from iku.config import Config
from iku.console import format_cyan, format_green, format_red, printMessage
from iku.info import IKU_INFO
from iku.core import synchronize_to_folder
from iku.driver import bind_iphone_drivers
from iku.parser import parse_args
from iku.tools import format_file_size
from iku.version import __version__

# stats / how much data synchronized
# progress report
# exception handling
# parallism
# other drivers?


def main() -> int:
    args = parse_args()

    if args is None:
        return 1

    if args.show_version:
        printMessage(__version__)
        return 0

    if args.show_info:
        printMessage(IKU_INFO)
        return 0

    drivers = bind_iphone_drivers()

    if args.command == "discover":
        table = tabulate(
            [[driver.name, driver.type] for driver in drivers],
            headers=["Name", "Type"],
            tablefmt="pretty",
        )
        printMessage(table)
        return 0

    Config.silent = args.silent
    Config.destructive = args.destructive

    if len(drivers) == 0:
        printMessage("No devices were detected on computer.")
        return 0

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
            printMessage(f"Please choose one from the following list of device names:")
            for driver in drivers:
                printMessage(f"- {driver.name}")
            return 1

    rc = 0
    start_time = time.time()

    try:
        result = synchronize_to_folder(selected_driver, args.folder)
        table = tabulate(
            [
                ["Files Analyzed", format_cyan(result.files_analyzed)],
                ["Files Written", format_cyan(result.details.files_written)],
                ["Files Skipped", format_cyan(result.details.files_skipped)],
                [
                    "Total Size of Files",
                    format_cyan(format_file_size(result.details.total_size)),
                ],
                [
                    "Size Written",
                    format_cyan(format_file_size(result.details.size_written)),
                ],
                [
                    "Size Skipped",
                    format_cyan(format_file_size(result.details.size_skipped)),
                ],
            ],
            tablefmt="pretty",
        )
        table_width = len(table.split("\n")[0])

        printMessage(f"+{'-' * (table_width - 2)}+")
        printMessage(f"| Summary{' ' * (table_width - 10)}|")
        printMessage(table)
    except KeyboardInterrupt:
        rc = 1

    total_seconds = round(time.time() - start_time, 2)
    status = format_green("[OK]") if not rc else format_red("[INTERRUPTED]")
    printMessage(f"{status} Elapsed time: {format_cyan(f'{total_seconds}s')}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
