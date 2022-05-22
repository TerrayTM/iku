import subprocess
from pathlib import Path
from time import time

tests = list(Path(".").rglob("test_*.py"))
start_time = time()

for test in tests:
    result = subprocess.run(
        ["python", "-m", str(test).replace("\\", ".").rstrip(".py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf8",
    )

    if result.returncode:
        print(test)
        print(result.stdout)
        break
else:
    print(f"[OK] Ran {len(tests)} test suites in {round(time() - start_time, 3)}s")
