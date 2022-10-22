"""Utility for browsing the project directory."""

from typing import Optional, Iterable
from pathlib import Path
from .. import settings


FILE_TYPES = set(settings.get("project.file_types"))
IGNORE_PATH_NAMES = settings.get("project.ignore_names")
IGNORE_PATH_MATCHES = settings.get("project.ignore_match")


def _recursive_files(dir: Path, depth: int):
    children = sorted(
        dir.iterdir(),
        key=lambda x: f"{int(not x.is_dir())}{x}",
    )
    for child in children:
        name = child.name
        if name in IGNORE_PATH_NAMES:
            continue
        s = str(child)
        if any(match in s for match in IGNORE_PATH_MATCHES):
            continue
        if child.is_dir():
            if depth == 0:
                yield child
            else:
                yield from _recursive_files(child, depth=depth - 1)
        elif child.is_file():
            if FILE_TYPES and child.suffix[1:] not in FILE_TYPES:
                continue
            yield child


def format_dir_tree(
    files: Iterable[Path],
    relative_dir: Optional[Path] = None,
) -> str:
    """Multiline string for *dir* contents as a tree matching *pattern* to *depth*."""
    if relative_dir is None:
        relative_dir = Path("/")
    path_strs = [str(relative_dir)]
    for path in (file.relative_to(relative_dir) for file in files):
        if path.is_dir():
            ps = f"  {path}/"
        else:
            ps = f"  {path}"
        path_strs.append(ps)
    return "\n".join(path_strs)


def search_files(dir: Path, pattern: str, max_depth: int = 10):
    """Generator of files in *dir* using *pattern*."""
    for child in _recursive_files(dir, max_depth):
        if pattern in str(child):
            yield(child)
