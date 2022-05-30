from iku.config import Config
from iku.constants import (CONSOLE_CYAN, CONSOLE_END_COLOR, CONSOLE_GREEN,
                           CONSOLE_RED)


def format_green(text: str) -> str:
    """
    Formats a string with green console color.

    Returns
    -------
    result : str
        A string with green console color.
    """
    return f"{CONSOLE_GREEN}{text}{CONSOLE_END_COLOR}"


def format_cyan(text: str) -> str:
    """
    Formats a string with cyan console color.

    Returns
    -------
    result : str
        A string with cyan console color.
    """
    return f"{CONSOLE_CYAN}{text}{CONSOLE_END_COLOR}"


def format_red(text: str) -> str:
    """
    Formats a string with red console color.

    Returns
    -------
    result : str
        A string with red console color.
    """
    return f"{CONSOLE_RED}{text}{CONSOLE_END_COLOR}"


def output(*values: object) -> None:
    """
    A wrapper function around console print to support the silent flag.
    """
    if not Config.silent:
        print(*values)


def clear_last_output() -> None:
    """
    Removes the last line of output to the console.
    """
    if not Config.silent:
        print("\033[A\033[A")
