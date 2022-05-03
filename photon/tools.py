from contextlib import contextmanager
from signal import signal
from typing import ContextManager
from tqdm import tqdm
from ctypes import WinError, byref, get_last_error, windll, wintypes


@contextmanager
def create_progress_bar(description, total) -> ContextManager:
    progress_bar = tqdm(
        desc=description, total=total, leave=False, unit="file", colour="green"
    )
    yield lambda: progress_bar.update()
    progress_bar.close()


@contextmanager
def prevent_keyboard_interrupt() -> ContextManager:
    handle = signal.signal(signal.SIGINT, signal.SIG_IGN)
    yield
    signal.signal(signal.SIGINT, handle)


def print_diff(diff) -> None:
    for diff_type, entries in diff.items():
        if len(entries) > 0:
            for entry in entries:
                print(f"{diff_type}{entry}")


def with_retry(callable, retries=3, args=()) -> bool:
    for _ in range(retries):
        if callable(*args):
            break
    else:
        return False
    return True


def write_ctime(filepath, timestamp):
    timestamp = int((timestamp * 10000000) + 116444736000000000)
    ctime = wintypes.FILETIME(timestamp & 0xFFFFFFFF, timestamp >> 32)
    handle = windll.kernel32.CreateFileW(filepath, 256, 0, None, 3, 128, None)

    if handle.value == wintypes.HANDLE(-1).value:
        raise WinError(get_last_error())

    if not wintypes.BOOL(windll.kernel32.SetFileTime(handle, byref(ctime), None, None)):
        raise WinError(get_last_error())

    if not wintypes.BOOL(windll.kernel32.CloseHandle(handle)):
        raise WinError(get_last_error())
