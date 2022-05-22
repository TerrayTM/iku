from pathlib import Path

for file in Path(".").rglob("*.py[co]"):
    file.unlink()

for folder in Path(".").rglob("__pycache__"):
    folder.rmdir()
