"""Utility for browsing the project directory."""

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


def format_dir_tree(dir: Path, depth: int = 10) -> str:
    """Multiline string for *dir* contents to *depth* as a tree."""
    all_paths = [
        file.relative_to(dir)
        for file in _recursive_files(dir, depth)
    ]
    path_strs = [str(dir)]
    for path in all_paths:
        if path.is_dir():
            ps = f"  {path}/"
        else:
            ps = f"  {path}"
        path_strs.append(ps)
    return "\n".join(path_strs)
