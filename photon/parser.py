import argparse
import os

from photon.indexer import Indexer


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="photon", description="Better tool for moving files.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        dest="show_version",
        help="Displays the currently installed version of isort.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        help="Shows verbose output, such as when files are skipped or when a check is successful.",
    )
    parser.add_argument(
        "-c",
        "--check-only",
        "--check",
        action="store_true",
        dest="check",
        help="Checks the file for unsorted / unformatted imports and prints them to the "
        "command line without modifying the file. Returns 0 when nothing would change and "
        "returns 1 when the file would be reformatted.",
    )
    parser.add_argument(
        "--base_folder",
        help="Provide the filename associated with a stream.",
    )
    return parser

def validate_args(args) -> bool:
    return True

def parse_args():
    parser = build_argument_parser()
    args = parser.parse_args()
    if not validate_args(args): 
        return
    return args



