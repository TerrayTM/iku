import csv
import hashlib
import os
from pathlib import Path
from typing import Dict, List

import win32api
import win32con

from photon.constants import (BUFFER_SIZE, DIFF_ADDED, DIFF_MODIFIED,
                              DIFF_REMOVED, INDEX_NAME)
from photon.exceptions import NotManagedByIndexException
from photon.types import IndexRow


class Indexer:
    def __init__(self, base_folder: str) -> None:
        self._index = {}
        self._rehash_items = []
        self._base_folder = base_folder
        self._file_path = os.path.join(base_folder, INDEX_NAME)
        self._diff_report = {DIFF_ADDED: [], DIFF_MODIFIED: [], DIFF_REMOVED: []}
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
                self._diff_report[DIFF_MODIFIED].append(key)
        else:
            self._diff_report[DIFF_ADDED].append(key)
        self._index[key] = value

    def _pop_index(self, key: str) -> None:
        self._index.pop(key)
        self._diff_report[DIFF_REMOVED].append(key)

    def _hash_file(self, file_path: str) -> str:
        file_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                file_hash.update(data)
        return file_hash.hexdigest()

    def destroy(self, relative_path: str) -> None:
        """
        Gets the difference between current index that is in-memory versus the index
        that is written on file.

        Returns
        -------
        result : Dict[str, List[str]]
            Dictionary of differences. For each entry, the key represents the difference
            type (add, modify, or remove) and the value is the relative paths.
        """
        if not relative_path in self._index:
            raise NotManagedByIndexException()

        self._pop_index(relative_path)
        os.unlink(os.path.join(self._base_folder, relative_path))

    def get_index(self, relative_path: str) -> IndexRow:
        if not relative_path in self._index:
            raise NotManagedByIndexException

        return self._index[relative_path]

    def synchronize(self, on_progress=None) -> None:
        keys = set()
        for relative_path in self.get_managed_relative_paths():
            file_path = os.path.join(self._base_folder, relative_path)
            keys.add(relative_path)
            last_modified = os.path.getmtime(file_path)
            size = os.path.getsize(file_path)
            if not self.match(relative_path, last_modified, size):
                file_hash = self._hash_file(file_path)
                self._set_index(relative_path, IndexRow(file_hash, last_modified, size))
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
        self._diff_report = {DIFF_ADDED: [], DIFF_MODIFIED: [], DIFF_REMOVED: []}
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

    def get_managed_relative_paths(self) -> List[str]:
        """
        Gets a list of relative paths that are managed by the indexer.

        Returns
        -------
        result : List[str]
            A list of relative paths.
        """
        return list(
            os.path.relpath(file_path, self._base_folder)
            for file_path in Path(os.path.join(self._base_folder)).rglob("*")
            if file_path.is_file()
            and os.path.relpath(file_path, self._base_folder) != INDEX_NAME
        )

    def count_managed_files(self) -> int:
        """
        Counts the number of files that are managed by the indexer.

        Returns
        -------
        result : int
            Number of managed files.
        """
        return len(self.get_managed_relative_paths())

    @property
    def diff_report(self) -> Dict[str, List[str]]:
        """
        Gets the difference between current index that is in-memory versus the index
        that is written on file.

        Returns
        -------
        result : Dict[str, List[str]]
            Dictionary of differences. For each entry, the key represents the difference
            type (add, modify, or remove) and the value is the relative paths.
        """
        return self._diff_report

    @property
    def index_path(self) -> str:
        return self._file_path

    @property
    def index_count(self) -> int:
        return len(self._index)
