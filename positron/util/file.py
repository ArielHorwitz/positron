"""Writing, loading, and opening files."""

from typing import Optional, Iterable
from loguru import logger
from dataclasses import dataclass
import os
import subprocess
import platform
from pathlib import Path
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
    """Return path relative to dir, or just path if not relative."""
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


def _child_sort(child, breadth_first):
    dir_val = child.is_dir() if breadth_first else not child.is_dir()
    return f"{int(dir_val)}{child}"


def yield_children(
    dir: Path,
    /,
    *,
    file_types: Optional[set[str]] = None,
    max_children: int = 1_000,
) -> Iterable[Path]:
    """Yield children of a directory."""
    assert dir.is_dir()
    count = 0
    for child in dir.iterdir():
        if file_types and child.is_file() and child.suffix not in file_types:
            continue
        yield child
        count += 1
        if count > max_children:
            break


def search_text(
    pattern: str,
    files: Iterable[Path],
    /,
    *,
    use_regex: bool = False,
    case_sensitive: bool = False,
    max_results: int = 0,
) -> list[tuple[FileCursor, str]]:
    """Use grep to find a pattern in files."""
    command_args = [
        "grep",
        "--with-filename",
        "--line-num",
        "--binary-files=without-match",
        "--ignore-case" if case_sensitive else "--no-ignore-case",
        "--basic-regexp" if use_regex else "--fixed-strings",
        pattern,
    ]
    results = []
    count = 0
    append = results.append
    for file in files:
        if not file.is_file():
            continue
        r = subprocess.run(command_args + [str(file)], capture_output=True, text=True)
        if r.stderr:
            raise ChildProcessError(r.stderr)
        grep_output = r.stdout
        for result in grep_output.split("\n"):
            if not result:
                continue
            file, line, text = result.split(":", 2)
            try:
                file = Path(file)
                line = int(line)
            except ValueError:
                logger.warning(f"Unexpected format from grep output: {line!r}")
                continue
            col = text.find(pattern)
            append((FileCursor(file, (line, col)), text))
            count += 1
            if max_results and count >= max_results:
                return results
    return results


USER_DIR = get_usr_dir("positron")
PROJ_DIR = Path(__file__).parent.parent.parent
