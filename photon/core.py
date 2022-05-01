import hashlib
import os
import time
from pathlib import Path

from tqdm import tqdm

from photon import indexer
from photon.driver import iPhoneDriver
from photon.indexer import Indexer
from ctypes import WinError, windll, wintypes, byref, get_last_error


def _with_retry(callable, retries=3, args=()) -> bool:
    for _ in range(retries):
        if callable(*args):
            break
    else:
        return False
    return True


def _write_ctime(filepath, timestamp):
    timestamp = int((timestamp * 10000000) + 116444736000000000)
    ctime = wintypes.FILETIME(timestamp & 0xFFFFFFFF, timestamp >> 32)
    handle = windll.kernel32.CreateFileW(filepath, 256, 0, None, 3, 128, None)
    if handle.value == wintypes.HANDLE(-1).value:
        raise WinError(get_last_error())
    if not wintypes.BOOL(windll.kernel32.SetFileTime(handle, byref(ctime), None, None)):
        raise WinError(get_last_error())
    if not wintypes.BOOL(windll.kernel32.CloseHandle(handle)):
        raise WinError(get_last_error())


def _write_to_target(target_path: str, file, indexer: Indexer) -> None:
    # need to stage the indexer so indexer doesnt update multiple times?
    source_hash = hashlib.md5()
    with open(target_path, "wb") as target_file:
        for data in file.read():
            source_hash.update(data)
            target_file.write(data)
    os.utime(target_path, (file.last_accessed, file.last_modified))
    _write_ctime(target_path, file.created_time)
    indexer.update(file.relative_path, file.last_modified, file.size)
    if not indexer.validate(file.relative_path, source_hash.hexdigest()):
        print("oh no")
        return False
    return True


def synchronize_files(
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
            if not _with_retry(_write_to_target, args=(target_path, file, indexer)):
                pass
        on_progress() if on_progress is not None else None

    for file in set(indexer.get_managed_file_paths()) - iphone_files:
        indexer.destroy(file)

    for dirpath, dirs, files in os.walk(base_folder):
        if not dirs and not files:
            os.rmdir(dirpath)


def create_progress_bar(total: int):
    progress_bar = tqdm(total=total, leave=False)
    return lambda: progress_bar.update()


def _print_diff(diff) -> None:
    for diff_type, entries in diff.items():
        if len(entries) > 0:
            for entry in entries:
                print(f"{diff_type}{entry}")


def begin_synchronization(driver: iPhoneDriver, base_folder: str) -> bool:
    indexer = Indexer(base_folder)
    indexer.synchronize(
        on_progress=None
    )  # create_progress_bar(indexer.count_managed_files()))
    _print_diff(indexer.diff_report)
    indexer.commit()
    synchronize_files(
        driver,
        base_folder,
        indexer,
        on_progress=None,  # create_progress_bar(driver.count_files()),
    )
    _print_diff(indexer.diff_report)
    indexer.commit()
    indexer.get_duplicates()
