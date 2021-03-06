from typing import Any


class NotManagedByIndexException(Exception):
    pass


class FileReadException(Exception):
    pass


class FileSeekException(Exception):
    pass


class KeyboardInterruptWithDataException(Exception):
    def __init__(self, data) -> None:
        super().__init__(None)
        self._data = data

    @property
    def data(self) -> Any:
        return self._data
