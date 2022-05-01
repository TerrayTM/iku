import hashlib
import os
import time
from pathlib import Path

from photon.driver import iPhoneDriver
from photon.indexer import Indexer


def synchronize_files(
    iphone_device: iPhoneDriver, base_folder: str, indexer: Indexer
) -> bool:
    iphone_files = set()
    for file in iphone_device.list_files():
        iphone_files.add(file)
        if indexer.match(file.path, file.last_modified, file.size):
            continue
        target_path = os.path.join(base_folder, file.path)
        source_hash = hashlib.md5()
        Path(os.path.dirname(target_path)).mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as target_file:
            while True:
                data = file.read()
                if not data:
                    break
                source_hash.update(data)
                target_file.write(data)
        indexer.update(file.path, file.last_modified, file.size)
        if not indexer.validate(file.path, source_hash.hexdigest()):
            pass
        time.sleep(0.1)


def run_tool(iphone_device: iPhoneDriver, base_folder: str) -> bool:
    index = Indexer(base_folder)
    index.synchronize()
    synchronize_files(iphone_device, base_folder, index)
    index.commit()
