from iku.config import Config
from iku.constants import CONSOLE_CYAN, CONSOLE_END_COLOR, CONSOLE_GREEN, CONSOLE_RED


def format_green(text: str) -> str:
    return f"{CONSOLE_GREEN}{text}{CONSOLE_END_COLOR}"


def format_cyan(text: str) -> str:
    return f"{CONSOLE_CYAN}{text}{CONSOLE_END_COLOR}"


def format_red(text: str) -> str:
    return f"{CONSOLE_RED}{text}{CONSOLE_END_COLOR}"


def printMessage(text: str) -> None:
    if not Config.silent:
        print(text)
