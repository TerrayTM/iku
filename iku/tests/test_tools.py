import os
import tempfile
from unittest import TestCase, main

from iku.constants import FILE_EMPTY
from iku.tools import format_file_size, write_ctime


class TestTools(TestCase):
    def test_create_progress_bar(self):
        pass

    def test_delay_keyboard_interrupt(self):
        pass

    def test_format_file_size(self):
        self.assertEqual(FILE_EMPTY, format_file_size(0))
        self.assertEqual("1.0 KB", format_file_size(1024))
        self.assertEqual("1.0 MB", format_file_size(1024 * 1024))
        self.assertEqual("1.0 GB", format_file_size(1024 * 1024 * 1024))
        self.assertEqual("1.0 TB", format_file_size(1024 * 1024 * 1024 * 1024))

    def test_write_ctime(self):
        with tempfile.NamedTemporaryFile() as file:
            write_ctime(file.name, 300)
            self.assertEqual(300, os.path.getctime(file.name))

    def test_write_ctime_invalid_name(self):
        self.assertRaises(OSError, write_ctime, "A", 300)


if __name__ == "__main__":
    main()
