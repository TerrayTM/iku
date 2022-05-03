import time

from click import prompt

from photon.core import begin_synchronization
from photon.driver import bind_iphone_drivers
from photon.parser import parse_args
from photon.version import __version__

# stats / how much data synchronized
# progress report
# exception handling
# parallism
# other drivers?
# logging


def main() -> int:
    args = parse_args()

    if args is None:
        return 1

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

    start_time = time.time()
    begin_synchronization(driver, args.folder)
    total_seconds = round(time.time() - start_time, 2)
    print(f"Elapsed time: {total_seconds}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
