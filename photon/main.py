import time

from click import prompt
from tabulate import tabulate

from photon.config import Config
from photon.console import format_cyan, format_green, format_red
from photon.core import synchronize_to_folder
from photon.driver import bind_iphone_drivers
from photon.parser import parse_args
from photon.tools import format_file_size
from photon.version import __version__

# stats / how much data synchronized
# progress report
# exception handling
# parallism
# other drivers?


def main() -> int:
    args = parse_args()

    if args is None:
        return 1

    Config.silent = args.silent
    Config.destructive = args.destructive

    if args.show_version:
        print(__version__)
        return 0

    drivers = bind_iphone_drivers()

    if len(drivers) == 0:
        print("No external storage detected")
        return 0

    driver = drivers[0]
    if len(drivers) > 1:
        print("Found the following drivers:")
        for index, driver in enumerate(drivers):
            print(f"    {index}) {driver.name}")
        selected = None
        while selected != "q":
            selected = prompt(f"Which one to use? (Enter 0-{len(drivers)}, q to quit)")
            if selected.isnumeric():
                index = int(selected)
                if index >= 0 and index < len(drivers):
                    driver = drivers[index]
                    break
        else:
            return 0

    rc = 0
    start_time = time.time()

    try:
        result = synchronize_to_folder(driver, args.folder)

        table = []
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
        print(f"+{'-' * (table_width - 2)}+")
        print(f"| Summary{' ' * (table_width - 10)}|")
        print(table)
    except KeyboardInterrupt:
        rc = 1

    total_seconds = round(time.time() - start_time, 2)
    status = format_green("[OK]") if not rc else format_red("[INTERRUPT]")
    print(f"{status} Elapsed time: {format_cyan(f'{total_seconds}s')}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
