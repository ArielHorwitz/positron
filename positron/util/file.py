"""Writing, loading, and opening files."""

from typing import Optional, Iterable
from dataclasses import dataclass
import os
import subprocess
import platform
import fuzzysearch
from pathlib import Path
from itertools import islice
import tomli


@dataclass(frozen=True)
class FileCursor:
    file: Path
    """File path."""
    cursor: tuple[int, int] = 1, 0
    """Cursor position as (line, column) tuple."""


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


def try_relative(path: Path, dir: Path) -> Path:
    return path.relative_to(dir) if path.is_relative_to(dir) else path


def format_dir_tree(
    files: Iterable[Path],
    relative_dir: Optional[Path] = None,
) -> str:
    """Multiline string for *dir* contents as a tree matching *pattern* to *depth*."""
    if relative_dir is None:
        relative_dir = Path("/")
    path_strs = [str(relative_dir)]
    for file in files:
        file = try_relative(file, relative_dir)
        if file.is_dir():
            ps = f"  {file}/"
        else:
            ps = f"  {file}"
        path_strs.append(ps)
    return "\n".join(path_strs)


def search_files(
    dir: Path,
    pattern: str,
    ignore_names: Optional[set[str]] = None,
    ignore_matches: Optional[set[str]] = None,
    file_types: Optional[set[str]] = None,
    breadth_first: bool = True,
    max_branching: int = 100,
    depth: int = 10,
) -> Iterable[Path]:
    """Generator of files in *dir* using *pattern*."""
    pattern = pattern.lower()
    ignore_names = [] if ignore_names is None else ignore_names
    ignore_matches = [] if ignore_matches is None else ignore_matches

    def child_sort(child):
        dir_val = child.is_dir() if breadth_first else not child.is_dir()
        return f"{int(dir_val)}{child}"

    children = islice(dir.iterdir(), max_branching)
    for child in sorted(children, key=child_sort):
        name = child.name
        if name in ignore_names:
            continue
        s = str(child)
        if any(match in s for match in ignore_matches):
            continue
        if child.is_dir():
            if depth == 0:
                yield child
            else:
                yield from search_files(
                    child,
                    pattern,
                    ignore_names,
                    ignore_matches,
                    file_types,
                    depth=depth - 1,
                )
        elif child.is_file():
            if pattern:
                fuzzy_matches = fuzzysearch.find_near_matches(
                    pattern,
                    s.lower(),
                    max_l_dist=10,
                    max_deletions=0,
                    max_insertions=10,
                    max_substitutions=0,
                )
                if not fuzzy_matches:
                    continue
            if file_types and child.suffix[1:] not in file_types:
                continue
            yield child


USER_DIR = get_usr_dir("positron")
PROJ_DIR = Path(__file__).parent.parent.parent
