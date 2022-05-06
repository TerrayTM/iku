import os
import random
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main
from iku.constants import DEVICE_IPHONE
from iku.driver import bind_iphone_drivers
from win32com.shell import shell
from iku.tests.tools import SequentialTestLoader
from pathlib import Path


class TestDriver(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        random.seed(42)
        base_folder = tempfile.mkdtemp()
        base_folder_pidl, _ = shell.SHParseDisplayName(base_folder, 0, None)
        desktop = shell.SHGetDesktopFolder()
        base_folder_interface = desktop.BindToObject(
            base_folder_pidl, None, shell.IID_IShellFolder
        )
        cls._base_folder = base_folder
        cls._get_desktop_function = shell.SHGetDesktopFolder
        shell.SHGetDesktopFolder = lambda: base_folder_interface

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(cls._base_folder)
        shell.SHGetDesktopFolder = cls._get_desktop_function

    def _write_random_file(self, relative_path: str, size: int) -> None:
        data = random.getrandbits(size * 8).to_bytes(size, sys.byteorder)
        with open(os.path.join(self._base_folder, relative_path), "wb") as file:
            file.write(data)

    def _create_folder(self, relative_path: str) -> None:
        Path(os.path.join(self._base_folder, relative_path)).mkdir(
            parents=True, exist_ok=True
        )

    def test_no_pc_folder(self) -> None:
        self._create_folder("A")
        self._create_folder("B")
        self._create_folder("C")
        self.assertEqual([], bind_iphone_drivers())

    def test_empty_pc_folder(self) -> None:
        self._create_folder("This PC")
        self.assertEqual([], bind_iphone_drivers())

    def test_one_driver_with_no_files(self) -> None:
        self._create_folder("This PC\\A")
        self._create_folder("This PC\\B\\Internal Storage")
        self._create_folder("This PC\\C\\Internal Storage\\DCIM")
        drivers = bind_iphone_drivers()
        self.assertEqual(1, len(drivers))
        self.assertEqual("C", drivers[0].name)
        self.assertEqual(DEVICE_IPHONE, drivers[0].type)
        self.assertEqual(0, drivers[0].count_files())
        self.assertEqual([], list(drivers[0].list_files()))

    def test_one_driver_with_files(self) -> None:
        self._create_folder("This PC\\C\\Internal Storage\\DCIM\\A")
        self._create_folder("This PC\\C\\Internal Storage\\DCIM\\B")
        self._create_folder("This PC\\C\\Internal Storage\\DCIM\\C")
        self._write_random_file("This PC\\C\\Internal Storage\\DCIM\\Z", 128)
        self._write_random_file("This PC\\C\\Internal Storage\\DCIM\\A\\Z", 128)
        self._write_random_file("This PC\\C\\Internal Storage\\DCIM\\A\\ZZ", 128)
        self._write_random_file("This PC\\C\\Internal Storage\\DCIM\\A\\ZZZ", 128)
        self._write_random_file("This PC\\C\\Internal Storage\\DCIM\\C\\Z", 128)
        self._write_random_file("This PC\\C\\Internal Storage\\DCIM\\C\\ZZ", 128)
        self._write_random_file("This PC\\C\\Internal Storage\\DCIM\\C\\ZZZ", 128)
        drivers = bind_iphone_drivers()
        self.assertEqual(1, len(drivers))
        self.assertEqual("C", drivers[0].name)
        self.assertEqual(DEVICE_IPHONE, drivers[0].type)
        self.assertEqual(6, drivers[0].count_files())
        self.assertEqual(
            ["A\\Z", "A\\ZZ", "A\\ZZZ", "C\\Z", "C\\ZZ", "C\\ZZZ"],
            list(sorted(file.relative_path for file in drivers[0].list_files())),
        )

    def test_multiple_drivers(self) -> None:
        self._create_folder("This PC\\One\\Internal Storage\\DCIM")
        self._create_folder("This PC\\Two\\Internal Storage\\DCIM\\Pictures")
        self._create_folder("This PC\\Three\\Internal Storage\\DCIM\\Pictures")
        self._write_random_file(
            "This PC\\Two\\Internal Storage\\DCIM\\Pictures\\Z", 128
        )
        self._write_random_file(
            "This PC\\Two\\Internal Storage\\DCIM\\Pictures\\ZZ", 128
        )
        self._write_random_file(
            "This PC\\Three\\Internal Storage\\DCIM\\Pictures\\ZZZ", 128
        )
        drivers = bind_iphone_drivers()
        self.assertEqual(4, len(drivers))
        self.assertEqual(
            ["C", "One", "Three", "Two"],
            list(sorted(driver.name for driver in drivers)),
        )
        self.assertEqual([DEVICE_IPHONE] * 4, list(driver.type for driver in drivers))
        sorted_drivers = list(sorted(drivers, key=lambda driver: driver.name))
        self.assertEqual(6, sorted_drivers[0].count_files())
        self.assertEqual(0, sorted_drivers[1].count_files())
        self.assertEqual(1, sorted_drivers[2].count_files())
        self.assertEqual(2, sorted_drivers[3].count_files())
        self.assertEqual(
            ["A\\Z", "A\\ZZ", "A\\ZZZ", "C\\Z", "C\\ZZ", "C\\ZZZ"],
            list(sorted(file.relative_path for file in sorted_drivers[0].list_files())),
        )
        self.assertEqual(
            [],
            list(sorted(file.relative_path for file in sorted_drivers[1].list_files())),
        )
        self.assertEqual(
            ["Pictures\\ZZZ"],
            list(sorted(file.relative_path for file in sorted_drivers[2].list_files())),
        )
        self.assertEqual(
            ["Pictures\\Z", "Pictures\\ZZ"],
            list(sorted(file.relative_path for file in sorted_drivers[3].list_files())),
        )

    def test_one_driver_in_computer_prefix(self) -> None:
        shutil.rmtree(os.path.join(self._base_folder, "This PC"))
        self._create_folder("Computer")
        self._create_folder("Computer\\A\\Internal Storage\\DCIM\\A")
        self._write_random_file("Computer\\A\\Internal Storage\\DCIM\\A\\Picture", 128)
        drivers = bind_iphone_drivers()
        self.assertEqual(1, len(drivers))
        self.assertEqual("A", drivers[0].name)
        self.assertEqual(DEVICE_IPHONE, drivers[0].type)
        self.assertEqual(1, drivers[0].count_files())
        self.assertEqual(
            ["A\\Picture"], list(file.relative_path for file in drivers[0].list_files())
        )


if __name__ == "__main__":
    main(testLoader=SequentialTestLoader(), failfast=True)
