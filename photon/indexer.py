import csv
import hashlib
import os
from glob import glob
from typing import Dict, List
from pathlib import Path

from tqdm import tqdm

from photon.constants import (
    BUFFER_SIZE,
    DIFF_ADDED,
    DIFF_MODIFIED,
    DIFF_REMOVED,
    INDEX_NAME,
)
from photon.types import IndexRow


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
            self._report[DIFF_MODIFIED].append(key)
        self._index[key] = value

    def _pop_index(self, key: str) -> None:
        self._index[key].pop(key)
        self._report[DIFF_MODIFIED].append(key)

    def _hash_file(self, file_path: str) -> str:
        file_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                file_hash.update(data)
        return file_hash.hexdigest()

    def synchronize(self) -> None:
        keys = set()
        for file in tqdm(Path(os.path.join(self._base_folder)).rglob("*")):
            if not file.is_file():
                continue
            file = str(file)
            if file == self._file_path:
                continue
            key = file.replace(self._base_folder + "\\", "")
            keys.add(key)
            last_modified = os.path.getmtime(file)
            size = os.path.getsize(file)
            if self.match(key, last_modified, size):
                continue
            file_hash = self._hash_file(file)
            self._set_index(key, IndexRow(file_hash, last_modified, size))
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
        with open(self._file_path, "w", newline="") as file:
            writer = csv.writer(file)
            for path, index_row in self._index.items():
                writer.writerow([path, *index_row])

    def match(self, path: str, last_modified: float, size: int) -> bool:
        return (
            path in self._index
            and self._index[path].last_modified == last_modified
            and self._index[path].size == size
        )

    def validate(self, path: str, source_hash: str) -> bool:
        return path in self._index and self._index[path].file_hash == source_hash

    @property
    def diff_report(self) -> Dict[str, List[str]]:
        return self._report

    @property
    def index_path(self) -> str:
        return self._file_path
