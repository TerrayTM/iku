import argparse
import os

from photon.index import Index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base-directory")
    args = parser.parse_args()
    if not os.path.isdir(args.path):
        return 1
    indexer = Index(args.path)
    indexer.update()
    indexer.save()


if __name__ == "__main__":
    raise SystemExit(main())
