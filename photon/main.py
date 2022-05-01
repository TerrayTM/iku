from click import prompt
from soupsieve import select
from tqdm import tqdm

from photon.core import begin_synchronization
from photon.driver import bind_iphone_drivers
from photon.parser import parse_args
from photon.version import __version__

# stats / how much data synchronized
# progress report
# exception handling
# parallism
# other drivers?


def main() -> int:
    args = parse_args()
    if args.show_version:
        print(__version__)
        return 0
    drivers = bind_iphone_drivers()

    if len(drivers) == 0:
        print("No drivers detected")
        return 1
    driver = drivers[0]
    if len(drivers) > 1:
        print("Found the following drivers:")
        for index, driver in enumerate(drivers):
            print(f"    {index}) {driver.name}")
        selected = None
        while selected != "q":
            selected = prompt(f"Which one to use? (Enter 0-{len(drivers)}, q to quit)")
            if (
                selected.isnumeric()
                and int(selected) >= 0
                and int(selected) < len(drivers)
            ):
                driver = drivers[int(selected)]
                break
    begin_synchronization(driver, args.folder)
    print("process complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
