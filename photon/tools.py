import math
import signal
from contextlib import contextmanager
from ctypes import WinError, byref, get_last_error, windll, wintypes
from typing import ContextManager

from tqdm import tqdm

from photon.config import Config


@contextmanager
def create_progress_bar(description, total) -> ContextManager:
    if Config.silent:

        def empty_function() -> None:
            pass

        yield empty_function
    else:
        progress_bar = tqdm(
            desc=description, total=total, leave=False, unit="file", colour="green"
        )
        yield lambda: progress_bar.update()
        progress_bar.close()


@contextmanager
def delay_keyboard_interrupt() -> ContextManager:
    interrupt_signal = None

    def interrupt_handler(sig, frame):
        nonlocal interrupt_signal
        interrupt_signal = (sig, frame)

    handler = signal.signal(signal.SIGINT, interrupt_handler)

    yield

    signal.signal(signal.SIGINT, handler)

    if interrupt_signal is not None:
        handler(*interrupt_signal)


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
    handle = wintypes.HANDLE(
        windll.kernel32.CreateFileW(filepath, 256, 0, None, 3, 128, None)
    )

    if handle.value == wintypes.HANDLE(-1).value:
        raise WinError(get_last_error())

    if not wintypes.BOOL(windll.kernel32.SetFileTime(handle, byref(ctime), None, None)):
        raise WinError(get_last_error())

    if not wintypes.BOOL(windll.kernel32.CloseHandle(handle)):
        raise WinError(get_last_error())


def format_file_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"

    size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"
