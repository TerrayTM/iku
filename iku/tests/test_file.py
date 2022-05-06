import os
import random
import sys
import tempfile
from iku.config import Config
from unittest import TestCase, main
from iku.exceptions import DeviceFileReadException
from iku.file import DeviceFile
from win32com.shell import shell, shellcon
from iku.tests.tools import SequentialTestLoader


class TestFile(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        random.seed(42)
        fd, path = tempfile.mkstemp()
        file = os.fdopen(fd, "wb")
        cls._data = random.getrandbits(8192).to_bytes(1024, sys.byteorder)
        file.write(cls._data)
        file.close()
        cls._parent_name = os.path.basename(os.path.dirname(path))
        cls._name = os.path.basename(path)
        cls._path = path
        parent_pidl, _ = shell.SHParseDisplayName(os.path.dirname(path), 0, None)
        desktop = shell.SHGetDesktopFolder()
        cls._parent_interface = desktop.BindToObject(
            parent_pidl, None, shell.IID_IShellFolder
        )
        for pidl in cls._parent_interface.EnumObjects(0, shellcon.SHCONTF_NONFOLDERS):
            if (
                cls._parent_interface.GetDisplayNameOf(pidl, shellcon.SHGDN_NORMAL)
                == cls._name
            ):
                cls._pidl = pidl
                break
        else:
            raise Exception()
        cls._buffer_size = Config.buffer_size
        Config.buffer_size = 128

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        Config.buffer_size = cls._buffer_size
        os.unlink(cls._path)

    def test_device_file(self) -> None:
        file = DeviceFile(self._pidl, self._parent_interface, self._parent_name)
        self.assertEqual(
            os.path.join(self._parent_name, self._name), file.relative_path
        )
        self.assertEqual(self._name, file.name)
        self.assertEqual(1024, file.size)
        self.assertAlmostEqual(os.path.getmtime(self._path), file.last_modified, 2)
        self.assertAlmostEqual(os.path.getctime(self._path), file.created_time, 2)
        self.assertAlmostEqual(os.path.getatime(self._path), file.last_accessed, 2)

    def test_device_file_read(self) -> None:
        file = DeviceFile(self._pidl, self._parent_interface, self._parent_name)
        read_data = list(data for data in file.read())
        self.assertEqual(8, len(read_data))
        self.assertEqual(self._data, b"".join(read_data))
        self.assertEqual([], list(file.read()))
        file.reset_seek()
        file.reset_seek()
        read_data = list(data for data in file.read())
        self.assertEqual(8, len(read_data))
        self.assertEqual(self._data, b"".join(read_data))

    def test_device_file_read_error(self) -> None:
        file = DeviceFile(self._pidl, self._parent_interface, self._parent_name)
        stream = file._stream

        class TestStream:
            def __init__(self, stream) -> None:
                self._counter = 0
                self._stream = stream

            def Read(self, size: int) -> bytes:
                self._counter += 1
                if self._counter != 2:
                    return self._stream.Read(size)
                raise Exception()

        file._stream = TestStream(stream)
        iterator = file.read()
        self.assertEqual(self._data[:128], next(iterator))
        self.assertRaises(DeviceFileReadException, lambda: next(iterator))
        file._stream = stream


if __name__ == "__main__":
    main(testLoader=SequentialTestLoader(), failfast=True)
