"""Writing, loading, and opening files."""
import os
import subprocess
import platform
from pathlib import Path
import tomli


def toml_load(file: Path) -> dict:
    """Load TOML *file* and returns a dictionary using `tomli`."""
    return tomli.loads(file_load(file))


def file_load(file: os.PathLike) -> str:
    """Loads *file* and returns the contents as a string."""
    with open(file, "r") as f:
        d = f.read()
    return d


def file_dump(file: os.PathLike, d: str, clear: bool = True):
    """Saves the string *d* to *file*.

    Will overwrite the file if *clear* is True, otherwise will append to it.
    """
    with open(file, "w" if clear else "a", encoding="utf-8") as f:
        f.write(d)


def open_path(path: os.PathLike):
    """Opens the given path. Method used is platform-dependent."""
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def get_usr_dir(dir_name: str) -> Path:
    r"""Return a path to a dedicated directory in the user's app data folder.

    - Windows: `~\AppData\Local\dir_name`
    - Mac OS: `~/Library/Local/dir_name`
    - Linux: `~/.local/share/dir_name`
    """
    if platform.system() == "Windows":
        parts = ["AppData", "Local"]
    elif platform.system() == "Darwin":
        parts = ["Library"]
    else:
        parts = [".local", "share"]
    path = Path.home().joinpath(*parts) / dir_name
    path.mkdir(parents=True, exist_ok=True)
    return path


USER_DIR = get_usr_dir("nide")
PROJ_DIR = Path.cwd()
