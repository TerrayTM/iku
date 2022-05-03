from contextlib import contextmanager
import csv
import hashlib
import os
from pathlib import Path
from typing import ContextManager, Dict, Iterator, List

import win32api
import win32con

from photon.constants import (
    BUFFER_SIZE,
    DIFF_ADDED,
    DIFF_MODIFIED,
    DIFF_REMOVED,
    INDEX_NAME,
)
from photon.exceptions import NotManagedByIndexException
from photon.tools import prevent_keyboard_interrupt
from photon.types import IndexRow, StagedIndexData


class Indexer:
    def __init__(self, base_folder: str) -> None:
        self._index = {}
        self._staged_index_data = None
        self._base_folder = base_folder
        self._index_path = os.path.join(base_folder, INDEX_NAME)
        self._diff_report = {DIFF_ADDED: [], DIFF_MODIFIED: [], DIFF_REMOVED: []}
        if os.path.exists(self._index_path):
            try:
                with open(self._index_path, newline="") as file:
                    reader = csv.reader(file)
                    for index_row in reader:
                        path, file_hash, last_modified, size = index_row
                        self._index[path] = IndexRow(
                            file_hash, float(last_modified), int(size)
                        )
            except csv.Error:
                self._index = {}
                os.unlink(self._index_path)

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

    @contextmanager
    def stage(self, path: str, relative_path: str) -> ContextManager:
        with prevent_keyboard_interrupt():
            backup_path = f"{path}.backup"
            self._staged_index_data = StagedIndexData(
                path, relative_path, backup_path, self._index.get(relative_path)
            )

            if os.path.isfile(path):
                os.rename(path, backup_path)

        yield

        with prevent_keyboard_interrupt():
            if os.path.isfile(backup_path):
                os.unlink(backup_path)

            self._staged_index_data = None

    def revert(self) -> None:
        if self._staged_index_data is None:
            return

        relative_path = self._staged_index_data.relative_path
        index_row = self._staged_index_data.index_row

        if index_row is None:
            if relative_path in self._index:
                self._index.pop(relative_path)
                self._diff_report[DIFF_ADDED].remove(relative_path)
        elif self._index[relative_path] != index_row:
            self._index[relative_path] = index_row
            self._diff_report[DIFF_MODIFIED].remove(relative_path)

        if os.path.exists(self._staged_index_data.path):
            os.unlink(self._staged_index_data.path)

        if os.path.isfile(self._staged_index_data.backup_path):
            os.rename(self._staged_index_data.backup_path, self._staged_index_data.path)

        self._staged_index_data = None

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
            keys.add(relative_path)

            file_path = os.path.join(self._base_folder, relative_path)
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
        if os.path.isfile(self._index_path):
            os.unlink(self._index_path)
        with open(self._index_path, "w", newline="") as file:
            writer = csv.writer(file)
            for path, index_row in self._index.items():
                writer.writerow([path, *index_row])
        win32api.SetFileAttributes(self._index_path, win32con.FILE_ATTRIBUTE_HIDDEN)

    def match(self, relative_path: str, last_modified: float, size: int) -> bool:
        """
        Checks if given relative path exists in index and if their last modified and
        size matches.

        Parameters
        ----------
        relative_path : str
            The relative path of the file.

        last_modified : float
            The last modified timestamp of the file.

        size : int
            The size in bytes of the file.

        Returns
        -------
        result : bool
            True if the data stored in the index matches the given ones. False
            otherwise.
        """
        return (
            relative_path in self._index
            and self._index[relative_path].last_modified == last_modified
            and self._index[relative_path].size == size
        )

    def validate(self, relative_path: str, source_hash: str) -> bool:
        """
        Compares the hash stored in the index with the source file hash.

        Parameters
        ----------
        relative_path : str
            The relative path of the file managed by the index.

        source_hash : str
            The MD5 hash of the source file.

        Returns
        -------
        result : bool
            True if the hashes match and false if they do not or the given relative path
            does not exist in index.
        """
        return (
            relative_path in self._index
            and self._index[relative_path].file_hash == source_hash
        )

    def find_duplicates(self, match_content_only: bool = True) -> List[List[str]]:
        """
        Finds all the duplicate files that the indexer manages.

        Parameters
        ----------
        match_content_only : bool (default=True)
            If set to true, it considers a file the same as another file if their hash
            is the same. If false, the file's last modified time as well as size is
            also checked in addition to the hash.

        Returns
        -------
        result : List[List[str]]
            List of groups of relative paths that are duplicates.
        """
        groups = {}

        for path, index_row in self._index.items():
            key = (
                index_row.file_hash
                if match_content_only
                else f"{index_row.file_hash}|{index_row.last_modified}|{index_row.size}"
            )
            groups.setdefault(key, []).append(path)

        return [group for group in groups.values() if len(group) > 1]

    def get_managed_relative_paths(self) -> Iterator[str]:
        """
        Gets the relative paths that are managed by the indexer.

        Returns
        -------
        result : Iterator[str]
            An iterator of the relative paths.
        """
        return (
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
        return len(list(self.get_managed_relative_paths()))

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
        """
        Gets the path of where the index is saved.

        Returns
        -------
        result : str
            The path of where the index is saved.
        """
        return self._index_path

    @property
    def index_count(self) -> int:
        """
        Gets the length of the in-memory index.

        Returns
        -------
        result : int
            The length of the in-memory index.
        """
        return len(self._index)
