import os
import random
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Iterator, List, Dict
from unittest import TestCase, main

from photon.types import IndexRow, StagedIndexData
from photon.constants import DIFF_ADDED, DIFF_MODIFIED, DIFF_REMOVED
from photon.indexer import Indexer
from photon.tests.tools import SequentialTestLoader
from photon.exceptions import NotManagedByIndexException


class TestIndexer(TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestIndexer, cls).setUpClass()
        cls._index_map = {
            "A": ("8a9a9852083a9023cb8bc343494ff572", "256"),
            "B": ("afc9f5872442d9a22f9a3dc30e7419a8", "256"),
            "C": ("0e02370a6aeb618c51dcb5f656e549ac", "256"),
            "one\\A": ("59d376361def8f07a9739f4226e728bf", "256"),
            "one\\B": ("904c9e9e06a3e97b79297dfe714eeda3", "256"),
            "one\\C": ("652fd60135c8ac639dfe4467f52292b1", "256"),
            "two\\A": ("55459c41b76ff615391d5550a9097c8f", "256"),
            "two\\B": ("986cb6fd8920c92dfc5c76614ae4c3e9", "256"),
            "two\\C": ("adf61c8ed5f7069c2758c3ea20f15c62", "256"),
            "two\\three\\A": ("b5a5bdc4bc02b299c1e889d68378e820", "256"),
            "two\\three\\B": ("d4b0bd58e7a0853618536fb665e71683", "256"),
            "two\\three\\C": ("b0feee50197ee5b5703afde4dbd5c52a", "256"),
        }
        base_folder = tempfile.mkdtemp()
        random.seed(42)
        for path in cls._index_map:
            full_path = os.path.join(base_folder, path)
            Path(os.path.dirname(full_path)).mkdir(parents=True, exist_ok=True)
            data = random.getrandbits(2048).to_bytes(256, sys.byteorder)
            with open(full_path, "wb") as file:
                file.write(data)
        cls._base_folder = base_folder

    @classmethod
    def tearDownClass(cls):
        super(TestIndexer, cls).tearDownClass()
        shutil.rmtree(cls._base_folder)

    def _generate_expected_index(self) -> Iterator[str]:
        for relative_path, items in self._index_map.items():
            file_hash, file_size = items
            last_modified = str(
                os.path.getmtime(os.path.join(self._base_folder, relative_path))
            )
            yield [relative_path, file_hash, float(last_modified), int(file_size)]

    def _generate_expected_index_raw(self) -> List[str]:
        return [
            ",".join(str(entry) for entry in row) + "\n"
            for row in self._generate_expected_index()
        ]

    def _generate_expected_index_rows(self) -> Dict[str, IndexRow]:
        return {row[0]: IndexRow(*row[1:]) for row in self._generate_expected_index()}

    def _write_random_file(self, relative_path: str, size: int) -> None:
        data = random.getrandbits(size * 8).to_bytes(size, sys.byteorder)
        with open(os.path.join(self._base_folder, relative_path), "wb") as file:
            file.write(data)

    def test_create_index(self) -> None:
        indexer = Indexer(self._base_folder)
        self.assertEqual(0, indexer.index_count)
        indexer.synchronize()
        self.assertEqual(
            indexer.diff_report,
            {
                DIFF_ADDED: list(self._index_map.keys()),
                DIFF_MODIFIED: [],
                DIFF_REMOVED: [],
            },
        )
        self.assertEqual(len(self._index_map), indexer.index_count)
        indexer.commit()
        self.assertTrue(os.path.isfile(indexer.index_path))
        with open(indexer.index_path) as file:
            self.assertEqual(file.readlines(), self._generate_expected_index_raw())

    def test_load_index(self) -> None:
        indexer = Indexer(self._base_folder)
        self.assertEqual(12, indexer.index_count)
        for key, value in self._generate_expected_index_rows().items():
            self.assertEqual(value, indexer.get_index(key))
        self.assertEqual(
            indexer.diff_report,
            {
                DIFF_ADDED: [],
                DIFF_MODIFIED: [],
                DIFF_REMOVED: [],
            },
        )

    def test_destroy(self) -> None:
        indexer = Indexer(self._base_folder)
        indexer.destroy("A")
        indexer.destroy("B")
        indexer.destroy("C")
        self.assertFalse(os.path.isfile(os.path.join(self._base_folder, "A")))
        self.assertFalse(os.path.isfile(os.path.join(self._base_folder, "B")))
        self.assertFalse(os.path.isfile(os.path.join(self._base_folder, "C")))
        self.assertEqual(
            indexer.diff_report,
            {
                DIFF_ADDED: [],
                DIFF_MODIFIED: [],
                DIFF_REMOVED: ["A", "B", "C"],
            },
        )
        self.assertRaises(NotManagedByIndexException, indexer.destroy, "Z")

    def test_synchronize(self) -> None:
        files = ["X", "one\\A", "two\\three\\A"]
        for file in files:
            data = random.getrandbits(2048).to_bytes(512, sys.byteorder)
            with open(os.path.join(self._base_folder, file), "wb") as file:
                file.write(data)
        indexer = Indexer(self._base_folder)
        self.assertEqual(12, indexer.index_count)
        counter = 0
        hash_counter = 0

        def update():
            nonlocal counter
            counter += 1

        hash_file = indexer._hash_file

        def hash_file_with_counter(path: str):
            nonlocal hash_counter
            hash_counter += 1
            return hash_file(path)

        indexer._hash_file = hash_file_with_counter
        indexer.synchronize(update)
        indexer._hash_file = hash_file
        self.assertEqual(10, indexer.index_count)
        self.assertEqual(10, counter)
        self.assertEqual(3, hash_counter)
        self.assertEqual(
            {
                diff_type: list(sorted(entries))
                for diff_type, entries in indexer.diff_report.items()
            },
            {
                DIFF_ADDED: ["X"],
                DIFF_MODIFIED: ["one\\A", "two\\three\\A"],
                DIFF_REMOVED: ["A", "B", "C"],
            },
        )
        self._index_map.pop("A")
        self._index_map.pop("B")
        self._index_map.pop("C")
        self._index_map["X"] = ("fb98d7474e92950ee053fd26e3b2fa11", "512")
        self._index_map["one\\A"] = ("8b1d18c509ade3d34801b8b48b7feb9c", "512")
        self._index_map["two\\three\\A"] = ("752ec720f887b0fcdff8b56128ab11b1", "512")
        indexer.commit()
        with open(indexer.index_path) as file:
            self.assertEqual(file.readlines(), self._generate_expected_index_raw())

    def test_update(self) -> None:
        indexer = Indexer(self._base_folder)
        self._write_random_file("value", 256)
        self._write_random_file("one\\value", 256)
        self._write_random_file("one\\A", 256)
        timestamp = os.path.getmtime(os.path.join(self._base_folder, "value"))
        indexer.update("value", timestamp, 256)
        self.assertEqual(
            indexer.get_index("value"),
            IndexRow("e9d58068fce4cf9b185bc5e41c757423", timestamp, 256),
        )
        timestamp = os.path.getmtime(os.path.join(self._base_folder, "one\\value"))
        indexer.update("one\\value", timestamp, 256)
        self.assertEqual(
            indexer.get_index("one\\value"),
            IndexRow("9f297dcc8acf39c43b08d8e99a53ab76", timestamp, 256),
        )
        timestamp = os.path.getmtime(os.path.join(self._base_folder, "one\\A"))
        indexer.update("one\\A", timestamp, 256)
        self.assertEqual(
            indexer.get_index("one\\A"),
            IndexRow("0b6bf4795989136bcce920caf113347e", timestamp, 256),
        )
        self.assertEqual(
            indexer.diff_report,
            {
                DIFF_ADDED: ["value", "one\\value"],
                DIFF_MODIFIED: ["one\\A"],
                DIFF_REMOVED: [],
            },
        )
        indexer.commit()
        self._index_map["value"] = ("e9d58068fce4cf9b185bc5e41c757423", "256")
        self._index_map["one\\value"] = ("9f297dcc8acf39c43b08d8e99a53ab76", "256")
        self._index_map["one\\A"] = ("0b6bf4795989136bcce920caf113347e", "256")

    def test_match(self) -> None:
        indexer = Indexer(self._base_folder)
        self.assertFalse(indexer.match("unknown", 100, 100))
        self.assertFalse(indexer.match("value", 100, 100))
        timestamp = os.path.getmtime(os.path.join(self._base_folder, "value"))
        self.assertFalse(indexer.match("value", timestamp, 100))
        self.assertTrue(indexer.match("value", timestamp, 256))

    def test_get_index_failed(self) -> None:
        indexer = Indexer(self._base_folder)
        self.assertRaises(NotManagedByIndexException, indexer.get_index, "Q")

    def test_validate(self) -> None:
        indexer = Indexer(self._base_folder)
        self.assertFalse(indexer.validate("W", "ABC"))
        self.assertFalse(indexer.validate("value", "ABC"))
        self.assertFalse(indexer.validate("value", "ABC"))
        self.assertTrue(indexer.validate("value", "e9d58068fce4cf9b185bc5e41c757423"))

    def test_find_duplicates(self) -> None:
        pass

    def test_get_managed_relative_paths(self) -> None:
        indexer = Indexer(self._base_folder)
        self.assertEqual(
            list(sorted(self._index_map.keys())),
            list(sorted(indexer.get_managed_relative_paths())),
        )

    def test_count_managed_files(self) -> None:
        indexer = Indexer(self._base_folder)
        self.assertEqual(len(self._index_map), indexer.count_managed_files())

    def test_stage_new_file(self) -> None:
        indexer = Indexer(self._base_folder)
        test_path = os.path.join(self._base_folder, "ABC")
        expected_data = StagedIndexData(
            test_path, "ABC", f"{test_path}.backup", None
        )  # use constnat
        self.assertIsNone(indexer.staged_index_data)
        with indexer.stage(expected_data.path, expected_data.relative_path):
            self.assertEqual(expected_data, indexer.staged_index_data)
        self.assertIsNone(indexer.staged_index_data)
        try:
            with indexer.stage(expected_data.path, expected_data.relative_path):
                raise KeyboardInterrupt
        except KeyboardInterrupt:
            pass
        self.assertEqual(expected_data, indexer.staged_index_data)

    def test_stage_existing_file(self) -> None:
        indexer = Indexer(self._base_folder)
        test_path = os.path.join(self._base_folder, "one\\value")
        expected_data = StagedIndexData(
            test_path,
            "one\\value",
            f"{test_path}.backup",
            indexer.get_index("one\\value"),
        )  # use constnat
        self.assertIsNone(indexer.staged_index_data)
        with indexer.stage(expected_data.path, expected_data.relative_path):
            self.assertEqual(expected_data, indexer.staged_index_data)
            self.assertTrue(os.path.isfile(expected_data.backup_path))
            self.assertFalse(os.path.isfile(expected_data.path))
        self.assertIsNone(indexer.staged_index_data)
        self.assertFalse(os.path.isfile(expected_data.backup_path))
        self.assertTrue(os.path.isfile(expected_data.path))
        try:
            with indexer.stage(expected_data.path, expected_data.relative_path):
                raise KeyboardInterrupt
        except KeyboardInterrupt:
            pass
        self.assertEqual(expected_data, indexer.staged_index_data)
        self.assertTrue(os.path.isfile(expected_data.backup_path))
        self.assertFalse(os.path.isfile(expected_data.path))

    def test_revert_new_file(self) -> None:
        indexer = Indexer(self._base_folder)

    def test_revert_existing_file(self) -> None:
        indexer = Indexer(self._base_folder)

    def test_load_index_failed(self) -> None:
        pass

    # def test


if __name__ == "__main__":
    main(testLoader=SequentialTestLoader(), failfast=True)
