import os
from typing import Iterator

from pythoncom import IID_IStream
from pywintypes import com_error

from iku.config import Config
from iku.exceptions import DeviceFileReadException, DeviceFileSeekException
from iku.types import PIDL, FileInfo, PyIShellFolder


class DeviceFile:
    def __init__(self, pidl: PIDL, parent: PyIShellFolder, parent_name: str) -> None:
        """
        Represents a file on a device and provides utilities for reading the file in
        chunks. A file read stream will be opened automatically upon construction.

        Parameters
        ----------
        pidl : PIDL
            The file PIDL.

        parent : PyIShellFolder
            The parent folder of the file.

        parent_name : str
            The name of the parent folder of the file.
        """
        self._pidl = pidl
        self._parent = parent
        self._stream = parent.BindToStorage(pidl, None, IID_IStream)
        self._file_info = FileInfo(*self._stream.Stat())
        self._relative_path = os.path.join(parent_name, self._file_info.name)

    def reset_seek(self) -> None:
        """
        Resets the seek of the file read stream to 0.
        """
        try:
            self._stream.Seek(0, 0)
        except com_error:
            raise DeviceFileSeekException()

    def reopen(self) -> bool:
        """
        Attempts to reopen the file stream for reading.

        Returns
        -------
        result : bool
            Whether the operation succeeded or not.
        """
        try:
            self._stream = self._parent.BindToStorage(self._pidl, None, IID_IStream)
            self._file_info = FileInfo(*self._stream.Stat())
        except com_error:
            return False

        return True

    def read(self) -> Iterator[bytes]:
        """
        Reads the file.

        Returns
        -------
        result : Iterator[bytes]
            An iterator of the file stream when read in bytes.
        """
        try:
            while True:
                chunk = self._stream.Read(Config.buffer_size)

                if not chunk:
                    break

                yield chunk
        except com_error:
            raise DeviceFileReadException()

    @property
    def relative_path(self) -> str:
        """
        Gets the relative path of the file.

        Returns
        -------
        result : str
            The relative path of the file.
        """
        return self._relative_path

    @property
    def name(self) -> str:
        """
        Gets the name of the file.

        Returns
        -------
        result : str
            The name of the file.
        """
        return self._file_info.name

    @property
    def size(self) -> int:
        """
        Gets the size of the file.

        Returns
        -------
        result : int
            The size of the file in bytes.
        """
        return self._file_info.size

    @property
    def last_modified(self) -> float:
        """
        Gets the timestamp of when the file was last modified.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.last_modified.timestamp()

    @property
    def created_time(self) -> float:
        """
        Gets the timestamp of when the file was created.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.created_time.timestamp()

    @property
    def last_accessed(self) -> float:
        """
        Gets the timestamp of when the file was last accessed.

        Returns
        -------
        result : float
            The timestamp in Unix seconds.
        """
        return self._file_info.last_accessed.timestamp()
