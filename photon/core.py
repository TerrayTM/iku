import hashlib
import os
import time
from pathlib import Path

from tqdm import tqdm

from photon import indexer
from photon.driver import iPhoneDriver
from photon.indexer import Indexer


def _with_retry(callable, retries=3, args=()) -> bool:
    for _ in range(retries):
        if callable(*args):
            break
    else:
        return False
    return True


def _write_to_target(target_path: str, file, indexer: Indexer) -> None:
    source_hash = hashlib.md5()
    with open(target_path, "wb") as target_file:
        while True:
            data = file.read()
            if not data:
                break
            source_hash.update(data)
            target_file.write(data)
    indexer.update(file.path, file.last_modified, file.size)
    if not indexer.validate(file.path, source_hash.hexdigest()):
        return False
    time.sleep(0.1)
    return True


def synchronize_files(
    iphone_device: iPhoneDriver,
    base_folder: str,
    indexer: Indexer,
    on_progress=None,
) -> bool:
    iphone_files = set()
    for file in iphone_device.list_files():
        iphone_files.add(file.path)
        if not indexer.match(file.path, file.last_modified, file.size):
            target_path = os.path.join(base_folder, file.path)
            Path(os.path.dirname(target_path)).mkdir(parents=True, exist_ok=True)
            if not _with_retry(_write_to_target, args=(target_path, file, indexer)):
                pass
        on_progress() if on_progress is not None else None

    # destructive
    for file in set(indexer.get_managed_file_paths()) - iphone_files:
        indexer.destroy(file)
        # remove files
        # remove empty folders


def create_progress_bar(total: int):
    progress_bar = tqdm(total=total)
    return lambda: progress_bar.update()


def begin_synchronization(iphone_device: iPhoneDriver, base_folder: str) -> bool:

    indexer = Indexer(base_folder)
    indexer.synchronize(on_progress=create_progress_bar(indexer.count_managed_files()))
    print(indexer.diff_report)
    indexer.commit()
    synchronize_files(
        iphone_device,
        base_folder,
        indexer,
        on_progress=create_progress_bar(iphone_device.count_files()),
    )
    print(indexer.diff_report)
    indexer.commit()
    # indexer.get_duplicates();
