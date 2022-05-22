import subprocess
import shutil

subprocess.check_call(["pip", "uninstall", "-y", "iku"])
shutil.rmtree("iku.egg-info")
