from iku.console import format_cyan
from iku.version import __version__

IKU_INFO = f"""
 _  _            
(_)| |           
 _ | |  _  _   _ 
| || | / )| | | |
| || |< ( | |_| |
|_||_| \_) \____|

v{__version__}

Try one of the following:
    {format_cyan("iku sync C:/path/to/folder")} - Sync device files to given folder. 
    {format_cyan("iku discover")} - Discover what devices are detected by the tool.
    {format_cyan("iku dedup")} - Remove duplicates of files.
    {format_cyan("iku --help")} - In-depth information iku's command-line options.

Visit https://terrytm.com for complete information about how to use iku.
"""
