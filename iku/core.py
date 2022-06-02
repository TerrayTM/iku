import hashlib
import time
from typing import Callable, Optional, Tuple

from iku.config import Config
from iku.console import clear_last_output, output
from iku.constants import STEP_ONE_TEXT, STEP_TWO_TEXT
from iku.exceptions import (FileReadException, FileSeekException,
                            KeyboardInterruptWithDataException)
from iku.file import DeviceFile
from iku.indexer import Indexer
from iku.provider import Provider
from iku.systems import FileSystem
from iku.tools import create_progress_bar
from iku.types import SynchronizationDetails, SynchronizationResult


def _write_to_target(
    fs: FileSystem, target_path: str, file: DeviceFile, indexer: Indexer
) -> Tuple[bool, bool]:
    try:
        with indexer.stage(target_path, file.relative_path):
            source_hash = hashlib.md5()
            file.reset_seek()

            with fs.open(target_path, "wb") as target_file:
                for data in file.read():
                    source_hash.update(data)
                    target_file.write(data)

            fs.utime(target_path, (file.last_accessed, file.last_modified))
            fs.ctime(target_path, file.created_time)
            indexer.update(file.relative_path)

            if not indexer.validate(
                file.relative_path,
                source_hash.hexdigest(),
                file.last_modified,
                file.size,
            ):
                indexer.revert()
                return False, True
    except (FileReadException, FileSeekException):
        indexer.revert()
        return False, file.reopen()
    except KeyboardInterrupt:
        indexer.revert()
        raise

    return True, False


def _synchronize_files(
    provider: Provider,
    consumer: FileSystem,
    base_folder: str,
    indexer: Indexer,
    total_files: int,
    on_progress: Optional[Callable[[], None]] = None,
) -> SynchronizationDetails:
    all_files = set()
    files_copied = 0
    files_skipped = 0
    size_discovered = 0
    size_copied = 0
    size_skipped = 0

    try:
        for index, file in enumerate(provider.list_files()):
            all_files.add(file.relative_path)
            size_discovered += file.size

            if not indexer.match(file.relative_path, file.last_modified, file.size):
                success = False
                target_path = consumer.join(base_folder, file.relative_path)
                consumer.mkdir(consumer.dirname(target_path))

                for _ in range(Config.retries):
                    success, should_retry = _write_to_target(
                        consumer, target_path, file, indexer
                    )

                    if success or not should_retry:
                        break

                if not success:
                    return SynchronizationDetails(
                        files_copied,
                        files_skipped,
                        size_discovered,
                        size_copied,
                        size_skipped,
                        target_path,
                    )

                files_copied += 1
                size_copied += file.size
            else:
                files_skipped += 1
                size_skipped += file.size

            on_progress() if on_progress is not None else None

            if index + 1 < total_files:
                time.sleep(Config.delay)
    except KeyboardInterrupt:
        raise KeyboardInterruptWithDataException(
            SynchronizationDetails(
                files_copied,
                files_skipped,
                size_discovered,
                size_copied,
                size_skipped,
                None,
            )
        )

    if Config.destructive:
        for file in set(indexer.get_managed_relative_paths()) - all_files:
            indexer.destroy(file)

        consumer.remove_empty_folders()

    return SynchronizationDetails(
        files_copied, files_skipped, size_discovered, size_copied, size_skipped, None,
    )


def synchronize_to_folder(
    provider: Provider, consumer: FileSystem, destination_folder: str
) -> SynchronizationResult:
    output("Enumerating objects...")

    try:
        indexer = Indexer(consumer, destination_folder)
        total_indices = indexer.count_managed_files()
        total_files = provider.count_files()
    except KeyboardInterrupt:
        clear_last_output()
        raise

    clear_last_output()

    try:
        with create_progress_bar(STEP_ONE_TEXT, total_indices) as on_progress:
            files_indexed = indexer.synchronize(on_progress)
    except KeyboardInterruptWithDataException as exception:
        result = SynchronizationResult(
            exception.data,
            total_indices,
            total_files,
            SynchronizationDetails(0, 0, 0, 0, 0, None),
            indexer.diff,
            Indexer.empty_diff(),
        )

        indexer.commit()
        raise KeyboardInterruptWithDataException(result)

    index_diff = indexer.diff
    indexer.commit()

    try:
        with create_progress_bar(STEP_TWO_TEXT, total_files) as on_progress:
            details = _synchronize_files(
                provider,
                consumer,
                destination_folder,
                indexer,
                total_files,
                on_progress,
            )
    except KeyboardInterruptWithDataException as exception:
        result = SynchronizationResult(
            files_indexed,
            total_indices,
            total_files,
            exception.data,
            index_diff,
            indexer.diff,
        )

        indexer.commit()
        raise KeyboardInterruptWithDataException(result)

    sync_diff = indexer.diff
    indexer.commit()

    return SynchronizationResult(
        files_indexed, total_indices, total_files, details, index_diff, sync_diff,
    )
