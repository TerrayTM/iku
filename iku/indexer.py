import csv
import gzip
import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, ContextManager, Dict, Iterator, List, Optional

import win32api
import win32con

from iku.config import Config
from iku.constants import (
    BACKUP_FILE_EXTENSION,
    DIFF_ADDED,
    DIFF_MODIFIED,
    DIFF_REMOVED,
    INDEX_NAME,
)
from iku.exceptions import (
    KeyboardInterruptWithDataException,
    NotManagedByIndexException,
)
from iku.tools import delay_keyboard_interrupt
from iku.types import IndexRow, StagedIndexData


class Indexer:
    def __init__(self, base_folder: str) -> None:
        """
        The indexer controls the state of the destination folder such as what files are
        present and what changes can be undone. Upon initialization, it will load the
        saved index file if there is one.

        Parameters
        ----------
        base_folder : str
            The base folder where the user wants to synchronize files to.
        """
        self._index = {}
        self._staged_index_data = None
        self._base_folder = base_folder
        self._index_path = os.path.join(base_folder, INDEX_NAME)
        self._diff = self.empty_diff()
        if os.path.exists(self._index_path):
            try:
                with gzip.open(self._index_path, "rt", newline="") as file:
                    reader = csv.reader(file)
                    for index_row in reader:
                        path, file_hash, last_modified, size = index_row
                        self._index[path] = IndexRow(
                            file_hash, float(last_modified), int(size)
                        )
            except (csv.Error, UnicodeDecodeError, OSError, EOFError):
                self._index = {}
                os.unlink(self._index_path)

    def _set_index(self, key: str, value: IndexRow) -> None:
        """
        Sets the index and updates the diff report.

        Parameters
        ----------
        key : str
            The key of the index to set.

        value : IndexRow
            The index row associated with the key.
        """
        if key in self._index:
            if value != self._index[key]:
                self._diff[DIFF_MODIFIED].append(key)
        else:
            self._diff[DIFF_ADDED].append(key)
        self._index[key] = value

    def _pop_index(self, key: str) -> None:
        """
        Removes the index and updates the diff report.

        Parameters
        ----------
        key : str
            The key of the index to pop.
        """
        self._index.pop(key)
        self._diff[DIFF_REMOVED].append(key)

    def _hash_file(self, path: str) -> str:
        """
        Computes the MD5 hash of a given file.

        Parameters
        ----------
        path : str
            The absolute path of the file.

        Returns
        -------
        result : str
            The MD5 hash of the file.
        """
        file_hash = hashlib.md5()

        with open(path, "rb") as f:
            while True:
                data = f.read(Config.buffer_size)

                if not data:
                    break

                file_hash.update(data)

        return file_hash.hexdigest()

    @staticmethod
    def empty_diff() -> Dict[str, List[str]]:
        """
        Creates a diff dictionary that represents no change.

        Returns
        -------
        result : Dict[str, List[str]]
            The empty diff dictionary.
        """
        return {DIFF_ADDED: [], DIFF_MODIFIED: [], DIFF_REMOVED: []}

    @contextmanager
    def stage(self, path: str, relative_path: str) -> ContextManager:
        """
        Prepares the indexer for potential changes to the file as given by path, or any
        update calls on relative path. Used for staging changes that could be reverted
        during the context.

        Parameters
        ----------
        path : str
            The absolute path of the file.

        relative_path : str
            The relative path of the file.

        Returns
        -------
        result : ContextManager
            Provides a context where any changes to the file or updates to the index
            relating to the relative path would be staged.
        """
        with delay_keyboard_interrupt():
            counter = 0
            backup_path = f"{path}{BACKUP_FILE_EXTENSION}"
            self._staged_index_data = StagedIndexData(
                path, relative_path, backup_path, self._index.get(relative_path)
            )
            #unit tested
            while os.path.isfile(backup_path):
                backup_path = f"{path}{counter}{BACKUP_FILE_EXTENSION}"
                counter += 1

            if os.path.isfile(path):
                os.rename(path, backup_path)

        yield

        with delay_keyboard_interrupt():
            if os.path.isfile(path):
                if os.path.isfile(backup_path):
                    os.unlink(backup_path)
            elif os.path.isfile(backup_path):
                os.rename(backup_path, path)

            self._staged_index_data = None

    def revert(self) -> None:
        """
        Reverts a change that is staged if there is one. Otherwise does nothing. This
        will undo any update calls to the index with the staged relative path as well
        as any destination file changes.
        """
        with delay_keyboard_interrupt():
            if self._staged_index_data is None:
                return

            relative_path = self._staged_index_data.relative_path
            index_row = self._staged_index_data.index_row

            if index_row is None:
                if relative_path in self._index:
                    self._index.pop(relative_path)
                    self._diff[DIFF_ADDED].remove(relative_path)
            elif self._index[relative_path] != index_row:
                self._index[relative_path] = index_row
                self._diff[DIFF_MODIFIED].remove(relative_path)

            if os.path.exists(self._staged_index_data.path):
                os.unlink(self._staged_index_data.path)

            if os.path.isfile(self._staged_index_data.backup_path):
                os.rename(
                    self._staged_index_data.backup_path, self._staged_index_data.path
                )

            self._staged_index_data = None

    def destroy(self, relative_path: str) -> None:
        """
        Removes the index row for the relative path from the index. Also deletes the
        file that the relative path points to.
        """
        if not relative_path in self._index:
            raise NotManagedByIndexException()

        self._pop_index(relative_path)
        os.unlink(os.path.join(self._base_folder, relative_path))

    def get_index(self, relative_path: str) -> IndexRow:
        """
        Gets the index row associated with the given relative path.

        Parameters
        ----------
        relative_path : str
            The relative path for the index row you want to query.

        Returns
        -------
        result : IndexRow
            The index row associated with the relative path.
        """
        if not relative_path in self._index:
            raise NotManagedByIndexException

        return self._index[relative_path]

    def synchronize(self, on_progress: Optional[Callable[[], None]] = None) -> int:
        """
        Synchronizes the in-memory index with what is actually present on the file
        system. Will also update the index diff report accordingly.

        Parameters
        ----------
        on_progress : Optional[Callable[[], None]]
            Event callback for reporting when progress is made.

        Returns
        -------
        result : int
            Number of files indexed.
        """
        keys = set()
        files_indexed = 0

        try:
            for relative_path in self.get_managed_relative_paths():
                with delay_keyboard_interrupt():
                    keys.add(relative_path)

                    file_path = os.path.join(self._base_folder, relative_path)
                    last_modified = os.path.getmtime(file_path)
                    size = os.path.getsize(file_path)

                    if not self.match(relative_path, last_modified, size):
                        file_hash = self._hash_file(file_path)
                        self._set_index(
                            relative_path, IndexRow(file_hash, last_modified, size)
                        )

                    on_progress() if on_progress is not None else None
                    files_indexed += 1
        except KeyboardInterrupt:
            raise KeyboardInterruptWithDataException(files_indexed)

        for removed_key in set(self._index.keys()) - keys:
            self._pop_index(removed_key)

        return files_indexed

    def update(self, relative_path: str) -> None:
        """
        Updates the index for the relative path with the given properties. This method
        will also compute and store the MD5 hash of the file.

        Parameters
        ----------
        relative_path : str
            The relative path for the index row you want to query.
        """
        path = os.path.join(self._base_folder, relative_path)

        if not os.path.isfile(path):
            raise FileNotFoundError()

        self._set_index(
            relative_path,
            IndexRow(
                self._hash_file(path),
                os.path.getmtime(path),
                os.path.getsize(path),
            ),
        )

    def commit(self) -> None:
        """
        Writes the in-memory index to the index file. Cannot be keyboard interrupted.
        """
        with delay_keyboard_interrupt():
            if all(len(value) == 0 for value in self._diff.values()):
                return

            self._diff = self.empty_diff()

            if os.path.isfile(self._index_path):
                os.unlink(self._index_path)

            with gzip.open(self._index_path, "wt", newline="") as file:
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

    def validate(
        self,
        relative_path: str,
        source_hash: str,
        source_last_modified: float,
        source_size: int,
    ) -> bool:
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
            self.match(relative_path, source_last_modified, source_size)
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
    def staged_index_data(self) -> Optional[StagedIndexData]:
        """
        Gets the staged index data if there is one.

        Returns
        -------
        result : Optional[StagedIndexData]
            The staged index data if there is one.
        """
        return self._staged_index_data

    @property
    def diff(self) -> Dict[str, List[str]]:
        """
        Gets the difference between current index that is in-memory versus the index
        that is written on file.

        Returns
        -------
        result : Dict[str, List[str]]
            Dictionary of differences. For each entry, the key represents the difference
            type (add, modify, or remove) and the value is the relative paths.
        """
        return self._diff

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
