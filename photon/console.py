from photon.constants import (CONSOLE_CYAN, CONSOLE_END_COLOR, CONSOLE_GREEN,
                              CONSOLE_RED)


def format_green(text):
    return f"{CONSOLE_GREEN}{text}{CONSOLE_END_COLOR}"


def format_cyan(text):
    return f"{CONSOLE_CYAN}{text}{CONSOLE_END_COLOR}"


def format_red(text):
    return f"{CONSOLE_RED}{text}{CONSOLE_END_COLOR}"
