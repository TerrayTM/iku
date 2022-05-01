import os
import random
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List
from unittest import TestCase, main

from photon.constants import DIFF_ADDED
from photon.indexer import Indexer


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

    def _generate_expected_index(self) -> List[str]:
        expected_index = []
        for relative_path, items in self._index_map.items():
            file_hash, file_size = items
            last_modified = str(
                os.path.getmtime(os.path.join(self._base_folder, relative_path))
            )
            expected_index.append(
                ",".join([relative_path, file_hash, last_modified, file_size]) + "\n"
            )
        return expected_index

    def test_create_index(self) -> None:
        indexer = Indexer(self._base_folder)
        self.assertEqual(0, indexer.index_count)
        indexer.synchronize()
        self.assertEqual(
            indexer.diff_report, {DIFF_ADDED: list(self._index_map.keys())}
        )
        self.assertEqual(len(self._index_map), indexer.index_count)
        indexer.commit()
        self.assertTrue(os.path.isfile(indexer.index_path))
        with open(indexer.index_path) as file:
            self.assertEqual(file.readlines(), self._generate_expected_index())

    def test_load_index(self) -> None:
        pass
        # Indexer("test")
        # pass

    # def test_load_index_failed(self) -> None:
    #     pass

    # def test


if __name__ == "__main__":
    main()
