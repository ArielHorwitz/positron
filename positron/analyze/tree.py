"""Directory tree indexing of structure and contents."""

from loguru import logger
from pathlib import Path
import os.path
import re
import arrow
from dataclasses import dataclass, field
from ..util.file import yield_children
from ..util.time import pingpong, pong
from ..util import settings


FILE_TYPES = set((f".{ft}" if ft else ft) for ft in settings.get("project.file_types"))
IGNORE_MATCHES = settings.get("project.ignore_names")
RE_IGNORE_PATHS = re.compile("|".join(IGNORE_MATCHES)) if IGNORE_MATCHES else None
INDEX_TIMEOUT_MS = settings.get("project.indexing_timeout") * 1000


@dataclass
class _CachedDir:
    path: Path
    modified: float = -1
    children: tuple = field(default_factory=tuple, repr=False)
    children_set: set = field(default_factory=set, repr=False)
    files: tuple = field(default_factory=tuple, repr=False)
    folders: tuple = field(default_factory=tuple, repr=False)

    def __hash__(self):
        return hash(self.path)


class DirectoryTree:
    def __init__(self, root: Path):
        assert root.is_dir()
        self.root = root.resolve()
        self._cache = {self.root: _CachedDir(self.root)}
        self._all_paths = {self.root}
        self._sorted_tree = [self.root]
        self.last_modified = -1
        self.reindex()

    @property
    def all_paths(self):
        return self._sorted_tree

    def print_tree(self, *args):
        for p in self._sorted_tree:
            print(p.relative_to(self.root))

    def reindex(self):
        prev_count = len(self._all_paths)
        with pingpong(logger=logger.debug, log=f"Full reindex: {self}") as p:
            self.__full_reindex(p)
        new_count = len(self._all_paths)
        if prev_count != new_count:
            logger.debug(f"  --> {new_count} items")

    def __full_reindex(self, p: float):
        _cache = self._cache
        _all_paths = self._all_paths
        require_sort = False
        check_dirs = set(_cache.keys())
        done_check = set()
        while check_dirs:
            if pong(p) >= INDEX_TIMEOUT_MS:
                raise TimeoutError(
                    f"Timed out while reindexing {self}. Try adding more filters."
                )
            path = check_dirs.pop()
            if path in done_check:
                continue
            done_check.add(path)
            # Get/create cache entry
            cdir = _cache.get(path)
            if not cdir:
                _cache[path] = cdir = _CachedDir(path)
            # Remove from cache and paths if no longer exists
            if not path.exists():
                _all_paths.discard(path)
                _all_paths -= cdir.children_set
                if path in _cache:
                    _cache.pop(path)
                continue
            # Refresh if cache is invalidated by modification time
            modified = os.path.getmtime(path)
            if cdir.modified != modified:
                self.last_modified = arrow.now()
                require_sort = True
                cdir.modified = modified
                # Update children and paths
                _all_paths -= cdir.children_set
                cdir.children = new_children = tuple(self.get_children_from_disk(path))
                cdir.children_set = new_children_set = set(new_children)
                _all_paths |= new_children_set
                # Differentiate between files and folders
                files, folders = [], []
                appendf, appendd = files.append, folders.append
                for c in new_children:
                    appendd(c) if c.is_dir() else appendf(c)
                cdir.files = tuple(files)
                cdir.folders = tuple(folders)
                # Check any potentially new folders
                check_dirs |= set(folders)
        if require_sort:
            self._sorted_tree = sorted(_all_paths, key=self.sort_folders_key)

    @classmethod
    def get_children_from_disk(
        cls,
        path: Path,
        use_file_types: bool = True,
        use_path_filter: bool = True,
    ) -> list[Path]:
        file_types = FILE_TYPES if use_file_types else []
        children = yield_children(path, file_types=file_types)
        if use_path_filter and RE_IGNORE_PATHS is not None:
            children = filter(
                lambda p: RE_IGNORE_PATHS.search(str(p)) is None,
                children,
            )
        return sorted(children, key=cls.sort_folders_key)

    def get_children(self, path: Path, /) -> tuple[Path, ...]:
        """Get children of a directory from cache."""
        return self._cache[path.resolve()].children

    def __repr__(self) -> str:
        return f"<DirectoryTree {len(self._all_paths)} paths @ {self.root}>"

    @staticmethod
    def sort_tree_key(c: Path) -> str:
        """Key function for sorting paths in a tree."""
        parents = reversed(c.parents)
        parts = (f"{0 if p.is_dir() else 1}{p.name}" for p in [*parents, c])
        return "/".join(parts)

    @staticmethod
    def sort_folders_key(c: Path) -> str:
        """Key function for sorting paths in a tree with folders first."""
        primary_sort = 0
        file_sort = "000"
        if c.is_file():
            primary_sort = 1
            file_sort = f"{len(c.parents):0>3}"
        return f"{primary_sort}{file_sort}{c}"
