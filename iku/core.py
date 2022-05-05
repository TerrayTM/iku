import hashlib
import os
from pathlib import Path

from iku.config import Config
from iku.constants import STEP_ONE_TEXT, STEP_TWO_TEXT
from iku.driver import iPhoneDriver
from iku.exceptions import DeviceFileReadException
from iku.file import DeviceFile
from iku.indexer import Indexer
from iku.tools import create_progress_bar, with_retry, write_ctime
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
    on_progress=None,
) -> SynchronizationResult:
    all_files = set()
    files_written = 0
    files_skipped = 0
    files_deleted = 0
    total_size = 0
    size_written = 0
    size_skipped = 0

    try:
        for file in driver.list_files():
            all_files.add(file.relative_path)
            total_size += file.size

            if not indexer.match(file.relative_path, file.last_modified, file.size):
                target_path = os.path.join(base_folder, file.relative_path)
                Path(os.path.dirname(target_path)).mkdir(parents=True, exist_ok=True)

                if not with_retry(_write_to_target, args=(target_path, file, indexer)):
                    return SynchronizationDetails(
                        files_written,
                        files_skipped,
                        files_deleted,
                        total_size,
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
        pass

    if Config.destructive:
        for file in set(indexer.get_managed_relative_paths()) - all_files:
            indexer.destroy(file)
            files_deleted += 1

        for dirpath, dirs, files in os.walk(base_folder):
            if not dirs and not files:
                os.rmdir(dirpath)

    return SynchronizationDetails(
        files_written,
        files_skipped,
        files_deleted,
        total_size,
        size_written,
        size_skipped,
        None,
    )


def synchronize_to_folder(
    driver: iPhoneDriver, base_folder: str
) -> SynchronizationResult:
    indexer = Indexer(base_folder)
    managed_files_count = indexer.count_managed_files()
    files_analyzed = managed_files_count

    try:
        with create_progress_bar(STEP_ONE_TEXT, managed_files_count) as on_progress:
            indexer.synchronize(on_progress)
    except KeyboardInterrupt:
        indexer.commit()
        raise

    index_diff_report = indexer.diff_report
    indexer.commit()

    try:
        total_files = driver.count_files()
        files_analyzed += total_files
        with create_progress_bar(STEP_TWO_TEXT, total_files) as on_progress:
            details = _synchronize_files(
                driver,
                base_folder,
                indexer,
                on_progress,
            )
    except KeyboardInterrupt:
        indexer.commit()
        raise

    sync_diff_report = indexer.diff_report
    indexer.commit()

    return SynchronizationResult(
        details.current_relative_path is None,
        files_analyzed,
        details,
        index_diff_report,
        sync_diff_report,
    )
