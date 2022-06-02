from typing import Iterator

from iku.file import File
from iku.systems import FileSystem


class Provider:
    def __init__(self, fs: FileSystem, source_folder: str) -> None:
        self._fs = fs
        self._source_folder = source_folder

    def list_files(self) -> Iterator[File]:
        for path in self._fs.rglob_files():
            try:
                handle = File(
                    self._fs, path, self._fs.relpath(path, self._source_folder)
                )
                yield handle
            finally:
                handle.close()

    def count_files(self) -> int:
        return len(self._fs.rglob_files())
