import hashlib
import os
import time
from pathlib import Path

from photon.driver import iPhoneDriver
from photon.index import Index


def synchronize_files(
    iphone_device: iPhoneDriver, base_folder: str, index: Index
) -> bool:
    iphone_files = set()
    for file in iphone_device.list_files():
        iphone_files.add(file)
        if index.match(file.path, file.last_modified, file.size):
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
        index.update(file.path, file.last_modified, file.size)
        if not index.validate(file.path, source_hash.hexdigest()):
            pass
        time.sleep(0.1)


def run_tool(iphone_device: iPhoneDriver, base_folder: str) -> bool:
    index = Index(base_folder)
    index.synchronize()
    synchronize_files(iphone_device, base_folder, index)
    index.commit()
