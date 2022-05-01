import argparse
import os

from photon.indexer import Indexer


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iku",
        description="Better tool for moving files.",
    )
    group = parser.add_mutually_exclusive_group()
    group2 = parser.add_argument_group()
    group.add_argument(
        "-v",
        "--version",
        action="store_true",
        dest="show_version",
        help="Displays the currently installed version of isort.",
    )
    group2.add_argument(
        "-s",
        "--silent",
        action="store_true",
        dest="silent",
        help="Do not show progress output.",
    )
    group2.add_argument(
        "--folder",
        help="The folder destination to synchronize the files to.",
    )
    group.add_argument_group(group2)
    return parser


def validate_args(args) -> bool:
    return True


def parse_args():
    parser = build_argument_parser()
    args = parser.parse_args()
    if not validate_args(args):
        return
    return args
