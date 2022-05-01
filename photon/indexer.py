import csv
import hashlib
import os
from pathlib import Path
from typing import Dict, List

from photon.constants import (
    BUFFER_SIZE,
    DIFF_ADDED,
    DIFF_MODIFIED,
    DIFF_REMOVED,
    INDEX_NAME,
)
from photon.types import IndexRow
import win32con, win32api


class Indexer:
    def __init__(self, base_folder: str) -> None:
        self._index = {}
        self._rehash_items = []
        self._base_folder = base_folder
        self._file_path = os.path.join(base_folder, INDEX_NAME)
        self._report = {DIFF_ADDED: [], DIFF_MODIFIED: [], DIFF_REMOVED: []}
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, newline="") as file:
                    reader = csv.reader(file)
                    for index_row in reader:
                        path, file_hash, last_modified, size = index_row
                        self._index[path] = IndexRow(
                            file_hash, float(last_modified), int(size)
                        )
            except csv.Error:
                self._index = {}
                os.unlink(self._file_path)

    def _set_index(self, key: str, value: IndexRow) -> None:
        if key in self._index:
            if value != self._index[key]:
                self._report[DIFF_MODIFIED].append(key)
        else:
            self._report[DIFF_ADDED].append(key)
        self._index[key] = value

    def _pop_index(self, key: str) -> None:
        self._index.pop(key)
        self._report[DIFF_REMOVED].append(key)

    def _hash_file(self, file_path: str) -> str:
        file_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                file_hash.update(data)
        return file_hash.hexdigest()

    def destroy(self, file):
        # assume file is managed by index
        self._pop_index(file)
        os.unlink(os.path.join(self._base_folder, file))

    def synchronize(self, on_progress=None) -> None:
        keys = set()
        for file in Path(os.path.join(self._base_folder)).rglob("*"):
            if not file.is_file():
                continue
            file = str(file)
            key = file.replace(f"{self._base_folder}{os.sep}", "")
            if key == INDEX_NAME:
                continue
            keys.add(key)
            last_modified = os.path.getmtime(file)
            size = os.path.getsize(file)
            if not self.match(key, last_modified, size):
                file_hash = self._hash_file(file)
                self._set_index(key, IndexRow(file_hash, last_modified, size))
            on_progress() if on_progress is not None else None
        for removed_key in set(self._index.keys()) - keys:
            self._pop_index(removed_key)

    def update(self, path: str, last_modified: float, size: int) -> None:
        self._set_index(
            path,
            IndexRow(
                self._hash_file(os.path.join(self._base_folder, path)),
                last_modified,
                size,
            ),
        )

    def commit(self) -> None:
        self._report = {DIFF_ADDED: [], DIFF_MODIFIED: [], DIFF_REMOVED: []}
        if os.path.isfile(self._file_path):
            os.unlink(self._file_path)
        with open(self._file_path, "w", newline="") as file:
            writer = csv.writer(file)
            for path, index_row in self._index.items():
                writer.writerow([path, *index_row])
        win32api.SetFileAttributes(self._file_path, win32con.FILE_ATTRIBUTE_HIDDEN)

    def match(self, path: str, last_modified: float, size: int) -> bool:
        return (
            path in self._index
            and self._index[path].last_modified == last_modified
            and self._index[path].size == size
        )

    def validate(self, path: str, source_hash: str) -> bool:
        return path in self._index and self._index[path].file_hash == source_hash

    def get_duplicates(self, match_content_only: bool = True) -> List[List[str]]:
        groups = {}
        for path, index_row in self._index.items():
            key = (
                index_row.file_hash
                if match_content_only
                else f"{index_row.file_hash}|{index_row.last_modified}|{index_row.size}"
            )
            groups.setdefault(key, []).append(path)
        return [group for group in groups.values() if len(group) > 1]

    def get_managed_file_paths(self) -> List[str]:
        return list(
            file
            for file in Path(os.path.join(self._base_folder)).rglob("*")
            if file.is_file() and str(file) != INDEX_NAME
        )

    def count_managed_files(self) -> int:
        return len(self.get_managed_file_paths())

    @property
    def diff_report(self) -> Dict[str, List[str]]:
        return self._report

    @property
    def index_path(self) -> str:
        return self._file_path

    @property
    def index_count(self) -> int:
        return len(self._index)
