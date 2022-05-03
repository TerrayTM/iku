import hashlib
import os
from pathlib import Path
from photon.exceptions import DeviceFileReadException
from photon.file import DeviceFile

from photon.tools import create_progress_bar, write_ctime, print_diff, with_retry
from photon.driver import iPhoneDriver
from photon.indexer import Indexer


def _write_to_target(target_path: str, file: DeviceFile, indexer: Indexer) -> bool:
    # need to stage the indexer so indexer doesnt update multiple times?
    # retries needs to reset seek on file
    try:
        with indexer.stage(target_path, file.relative_path):
            source_hash = hashlib.md5()
            file.reset_seek()

            with open(target_path, "wb") as target_file:
                for data in file.read():
                    source_hash.update(data)
                    target_file.write(data)

            os.utime(target_path, (file.last_accessed, file.last_modified))
            write_ctime(target_path, file.created_time)
            indexer.update(file.relative_path, file.last_modified, file.size)

            if not indexer.validate(file.relative_path, source_hash.hexdigest()):
                indexer.revert()
                return False
    except DeviceFileReadException:
        indexer.revert()
        return False
    except KeyboardInterrupt:
        indexer.revert()
        raise

    return True


def _synchronize_files(
    iphone_device: iPhoneDriver,
    base_folder: str,
    indexer: Indexer,
    on_progress=None,
) -> bool:
    iphone_files = set()

    for file in iphone_device.list_files():
        iphone_files.add(file.relative_path)

        if not indexer.match(file.relative_path, file.last_modified, file.size):
            target_path = os.path.join(base_folder, file.relative_path)
            Path(os.path.dirname(target_path)).mkdir(parents=True, exist_ok=True)

            if not with_retry(_write_to_target, args=(target_path, file, indexer)):
                return False

        import time

        time.sleep(10)
        on_progress() if on_progress is not None else None

    # for file in set(indexer.get_managed_relative_paths()) - iphone_files:
    #     print(indexer.get_managed_relative_paths())
    #     indexer.destroy(file)

    # for dirpath, dirs, files in os.walk(base_folder):
    #     if not dirs and not files:
    #         os.rmdir(dirpath)
    return True


def begin_synchronization(driver: iPhoneDriver, base_folder: str) -> bool:
    indexer = Indexer(base_folder)

    with create_progress_bar(
        "Indexing (step 1/2)", indexer.count_managed_files()
    ) as on_progress:
        indexer.synchronize(on_progress)

    # print_diff(indexer.diff_report)
    indexer.commit()

    with create_progress_bar(
        "Synchronizing (step 2/2)", driver.count_files()
    ) as on_progress:
        _synchronize_files(
            driver,
            base_folder,
            indexer,
            on_progress,
        )

    # print_diff(indexer.diff_report)
    indexer.commit()
