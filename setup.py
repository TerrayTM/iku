import re

from setuptools import setup

with open("iku/version.py", "r", encoding="utf-8") as file:
    version = file.readline()

match = re.match(r"^__version__ = \"([\d\.]+)\"$", version)

if match:
    __version__ = match.group(1)
else:
    raise RuntimeError()

with open("README.md", "r", encoding="utf-8") as file:
    long_description = file.read()

setup(
    name="iku",
    packages=["iku"],
    version=__version__,
    description="Fast and resumable device-to-PC file synchronization tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Terry Zheng",
    author_email="contact@terrytm.com",
    maintainer="Terry Zheng",
    maintainer_email="contact@terrytm.com",
    url="https://iku.terrytm.com",
    python_requires=">=3.8",
    keywords="device file synchronization",
    license="Apache 2.0",
    zip_safe=False,
    install_requires=["pywin32", "tqdm", "tabulate"],
    project_urls={
        "Bug Reports": "https://iku.terrytm.com/issues",
        "Documentation": "https://iku.terrytm.com",
        "Source Code": "https://github.com/TerrayTM/iku",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Topic :: System :: Filesystems",
        "Operating System :: Microsoft :: Windows",
    ],
    entry_points={"console_scripts": ["iku = iku.main:main"]},
)
