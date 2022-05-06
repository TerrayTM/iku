import argparse
import os
from typing import Optional

from numpy import require
from iku.console import printMessage


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iku",
        description="Fast and resumable device-to-PC file synchronization tool.",
    )

    exclusive_args = parser.add_mutually_exclusive_group()
    exclusive_args.add_argument(
        "-v",
        "--version",
        action="store_true",
        dest="show_version",
        help="Displays the currently installed version of iku.",
    )
    exclusive_args.add_argument(
        "-i",
        "--info",
        action="store_true",
        dest="show_info",
        help="Shows a quick guide to using iku and some links to additional resources.",
    )

    subparsers = parser.add_subparsers(help="Command to execute.", dest="command")
    sync_parser = subparsers.add_parser(
        "sync", help="Synchronize device files to computer."
    )
    discover_parser = subparsers.add_parser(
        "discover", help="Discovers what devices are connected."
    )

    sync_parser.add_argument("folder", help="Path of the folder to sync the files to.")
    sync_parser.add_argument(
        "-n",
        "--device-name",
        dest="device_name",
        help="The device name of where to find the source files if there are multiple "
        "devices detected.",
    )
    sync_parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        dest="silent",
        help="Prevent from displaying any console output.",
    )
    sync_parser.add_argument(
        "-d",
        "--destructive",
        action="store_true",
        dest="destructive",
        help="Removes files and folders that does not exist in target device.",
    )
    sync_parser.add_argument(
        "--delay",
        type=float,
        dest="delay",
        help="Removes files and folders that does not exist in target device.",
    )
    sync_parser.add_argument(
        "-id",
        "--export-index-diff",
        dest="index_diff_path",
        help="Writes the index diff to the given location.",
    )
    sync_parser.add_argument(
        "-sd",
        "--show-sync-diff",
        dest="sync_diff_path",
        help="Writes the sync diff to the given location.",
    )

    return parser


def _validate_args(args) -> bool:
    if not args.command and not args.show_version and not args.show_info:
        printMessage("Need to specify an action.")
        return False

    if args.command:
        if args.show_version or args.show_info:
            printMessage("Cannot show version/info while executing an action.")
            return False

    if args.command == "sync":
        if not os.path.isdir(args.folder):
            printMessage("An invalid directory is given.")
            return False

        if args.delay < 0:
            printMessage("nope")
            return False

        args.folder = os.path.abspath(args.folder)

    return True


def parse_args() -> Optional[argparse.Namespace]:
    parser = _build_argument_parser()
    args = parser.parse_args()

    if not _validate_args(args):
        return None

    return args
