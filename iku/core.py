import hashlib
import os
from pathlib import Path
from typing import Callable, Optional

from iku.config import Config
from iku.constants import STEP_ONE_TEXT, STEP_TWO_TEXT
from iku.driver import iPhoneDriver
from iku.exceptions import DeviceFileReadException, KeyboardInterruptWithDataException
from iku.file import DeviceFile
from iku.indexer import Indexer
from iku.tools import create_progress_bar, write_ctime
from iku.types import SynchronizationDetails, SynchronizationResult


def _write_to_target(target_path: str, file: DeviceFile, indexer: Indexer) -> bool:
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
    driver: iPhoneDriver,
    base_folder: str,
    indexer: Indexer,
    on_progress: Optional[Callable[[], None]] = None,
) -> SynchronizationResult:
    all_files = set()
    files_written = 0
    files_skipped = 0
    size_discovered = 0
    size_written = 0
    size_skipped = 0

    try:
        for file in driver.list_files():
            all_files.add(file.relative_path)
            size_discovered += file.size
            import time

            time.sleep(10)
            if not indexer.match(file.relative_path, file.last_modified, file.size):
                target_path = os.path.join(base_folder, file.relative_path)
                Path(os.path.dirname(target_path)).mkdir(parents=True, exist_ok=True)

                if not any(
                    _write_to_target(target_path, file, indexer) for _ in range(3)
                ):
                    return SynchronizationDetails(
                        files_written,
                        files_skipped,
                        size_discovered,
                        size_written,
                        size_skipped,
                        target_path,
                    )  # should be full path

                files_written += 1
                size_written += file.size
            else:
                files_skipped += 1
                size_skipped += file.size

            on_progress() if on_progress is not None else None
    except KeyboardInterrupt:
        raise KeyboardInterruptWithDataException(
            SynchronizationDetails(
                files_written,
                files_skipped,
                size_discovered,
                size_written,
                size_skipped,
                None,
            )
        )

    if Config.destructive:
        for file in set(indexer.get_managed_relative_paths()) - all_files:
            indexer.destroy(file)

        for dirpath, dirs, files in os.walk(base_folder):
            if not dirs and not files:
                os.rmdir(dirpath)

    return SynchronizationDetails(
        files_written,
        files_skipped,
        size_discovered,
        size_written,
        size_skipped,
        None,
    )


def synchronize_to_folder(
    driver: iPhoneDriver, base_folder: str
) -> SynchronizationResult:
    indexer = Indexer(base_folder)
    total_files = driver.count_files()

    try:
        with create_progress_bar(
            STEP_ONE_TEXT, indexer.count_managed_files()
        ) as on_progress:
            files_indexed = indexer.synchronize(on_progress)
    except KeyboardInterruptWithDataException as exception:
        result = SynchronizationResult(
            exception.data,
            total_files,
            SynchronizationDetails(0, 0, 0, 0, 0, None),
            indexer.diff_report,
            Indexer.empty_diff(),
        )

        indexer.commit()
        raise KeyboardInterruptWithDataException(result)

    index_diff_report = indexer.diff_report
    indexer.commit()

    try:
        with create_progress_bar(STEP_TWO_TEXT, total_files) as on_progress:
            details = _synchronize_files(
                driver,
                base_folder,
                indexer,
                on_progress,
            )
    except KeyboardInterruptWithDataException as exception:
        result = SynchronizationResult(
            files_indexed,
            total_files,
            exception.data,
            index_diff_report,
            indexer.diff_report,
        )

        indexer.commit()
        raise KeyboardInterruptWithDataException(result)

    sync_diff_report = indexer.diff_report
    indexer.commit()

    return SynchronizationResult(
        files_indexed,
        total_files,
        details,
        index_diff_report,
        sync_diff_report,
    )
