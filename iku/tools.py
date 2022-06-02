import math
import signal
from contextlib import contextmanager
from ctypes import WinError, byref, get_last_error, windll, wintypes
from typing import ContextManager

from tqdm import tqdm

from iku.config import Config
from iku.constants import FILE_EMPTY, FILE_SIZES


@contextmanager
def create_progress_bar(description: str, total: int) -> ContextManager:
    if Config.silent:
        yield lambda: None
    else:
        progress_bar = tqdm(desc=description, total=total, leave=False, unit="file")

        try:
            yield lambda: progress_bar.update() or progress_bar.refresh()
        finally:
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


def write_ctime(filepath: str, timestamp: float):
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
        return FILE_EMPTY

    index = int(math.floor(math.log(size_bytes, 1024)))
    size = round(size_bytes / math.pow(1024, index), 2)

    return f"{size} {FILE_SIZES[index]}"
