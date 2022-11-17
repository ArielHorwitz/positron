"""Project session for analysis."""

from loguru import logger
from typing import Optional
from itertools import islice
from pathlib import Path
import traceback
import re
import json
import jedi
from jedi import Script
from jedi.api.classes import Name
from ..util.file import file_load, file_dump, USER_DIR, CACHE_DIR, FileCursor
from ..util.code import CodeError
from ..util import settings
from .linter import lint_text
from .tree import DirectoryTree


FILE_TYPE_ICONS = {
    # Languages
    ".py": "",  # 
    ".pyc": "",
    ".pyx": "",
    ".pxd": "",
    ".js": "",
    ".ts": "",
    ".rs": "",
    ".c": "",
    ".cpp": "",
    ".php": "",
    ".html": "",
    ".css": "",
    # Archives
    ".zip": "",
    ".tar.gz": "",
    ".7zip": "",
    # Audio
    ".wav": "ﱘ",
    ".mp3": "ﱘ",
    ".flac": "ﱘ",
    ".ogg": "ﱘ",
    ".m4a": "ﱘ",
    # Images
    ".png": "",
    ".jpg": "",
    ".jpeg": "",
    # Video
    ".mp4": "辶",
    ".ogv": "辶",
    ".mkv": "辶",
    # Configs
    ".yml": "",
    ".yaml": "",
    ".toml": "",
    ".ini": "",
    ".cfg": "",
    # Miscallaneous
    ".md": "",
    ".json": "ﬥ",
    ".log": "",
    ".sh": "",
    ".bak": "",
}


class _Prefixes:
    @classmethod
    def _update_settings(cls, *args):
        logger.debug("Session _Prefixes updating settings")
        cls.proj = settings.get("path_prefixes.project")
        cls.config = settings.get("path_prefixes.config")
        cls.home = settings.get("path_prefixes.home")
        paths = []
        paths = []
        for replacement in settings.get("path_prefixes.custom"):
            original, new = replacement.split(";")
            original = Path(original).expanduser().resolve()
            paths.append((original, new))
        paths = sorted(paths, key=lambda x: -len(x[0].parents))
        logger.debug(
            f"Prefixes - "
            f"project: {cls.proj!r}, config: {cls.config!r}, home: {cls.home!r}"
        )
        logger.debug(
            "Path prefix replacements: "
            + " ; ".join(f"{p} -> {r}" for p, r in paths)
        )
        cls.paths = paths


# Bind settings
for n in filter(lambda x: x.startswith("path_prefixes."), settings.get_names()):
    settings.bind(n, _Prefixes._update_settings)
_Prefixes._update_settings()

SESSION_FILES_CACHE = CACHE_DIR / "sessions.json"
RE_TRAILING_WHITESPACE = re.compile(r"( +)\n")
RE_NEWLINE = re.compile(r"\n")


class Session:
    def __init__(self, project_path: Path, env_path: Optional[Path] = None):
        self.__file_mode = None
        if not project_path.is_dir():
            self.__file_mode = project_path
            project_path = project_path.parent
        self.project_path = project_path.expanduser().resolve()
        logger.info(f"Creating project:     {self.project_path}")
        if env_path is None:
            all_venvs = list(jedi.find_virtualenvs(paths=[self.project_path]))
            logger.info("Available environments:")
            logger.info("\n".join(f"  {v.executable}" for v in all_venvs))
            env_path = all_venvs[-1].executable
        self.env_path = Path(env_path).expanduser().resolve()
        self.dir_tree = DirectoryTree(self.project_path)
        self._project = jedi.Project(
            str(self.project_path),
            environment_path=str(self.env_path),
        )
        logger.info(
            f"Created project {self.project_path}"
            f" with environment: {self.env_path}"
        )

    def get_completions(
        self,
        path: Path,
        code: str,
        line: int,
        col: int,
        max_completions: int,
        fuzzy: bool = False,
    ) -> list[str]:
        """List of strings to complete code under the cursor."""
        script = jedi.Script(code=code, path=path, project=self._project)
        try:
            completions = script.complete(line, col, fuzzy=fuzzy)
        except Exception as e:
            logger.warning(f"get_completions exception: {e}")
            return []
        return islice(completions, max_completions)

    def get_context(self, path: Path, code: str, line: int, col: int):
        script = jedi.Script(code=code, path=path, project=self._project)
        return script.get_context(line, col)

    def get_info(self, path: Path, code: str, line: int, col: int) -> str:
        """Multiline string of code analysis under the cursor."""
        logger.debug(f"Getting info for: {path} :: {line},{col}")
        script = jedi.Script(code=code, path=path, project=self._project)
        debug_strs = []
        strs = []
        append = strs.append
        extend = strs.extend

        # Definitions
        names = list(script.help(line, col))
        if names:
            append(_title_break(f"{len(names)} Definitions"))
            append("\n==========\n".join(_format_object(script, n) for n in names))
            debug_strs.append(_format_object_debug(names[0]))

        # References
        refs = list(script.get_references(line, col))
        if refs:
            append(_title_break(f"{len(refs)} References"))
            extend(_format_object_short(script, r) for r in refs)

        # Debug
        if debug_strs:
            append(_title_break("Debug"))
            extend(debug_strs)

        # All module names
        if not names and not refs:
            names = list(script.get_names(all_scopes=True))
            append(_title_break(f"All {len(names)} module definitions"))
            if names:
                extend(
                    _format_object_short(script, n)
                    for n in names
                    if n.type in {"class", "function"}
                )
            else:
                append("No names found...")

        return "\n".join(strs)

    def search_project(
        self,
        string: str,
        do_complete: bool = True,
        exhaustive: bool = True,
    ):
        """Search the project."""
        if not string:
            return
        string = string.strip()
        if do_complete:
            try:
                yield from self._project.complete_search(string, all_scopes=exhaustive)
            except Exception as e:
                logger.warning("".join(traceback.format_exception(e)))
                logger.warning(f"Search project failed on string: {string!r}")
            return
        yield from self._project.search(string, all_scopes=exhaustive)

    def get_errors(self, code: str) -> list[CodeError]:
        script = jedi.Script(code=code, project=self._project)
        errors = []
        append = errors.append
        # Syntax errors from jedi
        for e in script.get_syntax_errors():
            msg = e.get_message()
            _, __, msg = msg.partition("Error: ")
            append(CodeError(msg, e.line, e.column))
        # Linter errors
        linter_errors = lint_text(code)
        errors.extend(linter_errors)
        return errors

    def get_file_cursors(self) -> list[FileCursor]:
        """Files and cursor positions for this session in cache."""
        if self.__file_mode:
            return [FileCursor(self.__file_mode)]
        # Retrieve entries from cache and convert
        if SESSION_FILES_CACHE.exists():
            session_cache = json.loads(file_load(SESSION_FILES_CACHE))
        else:
            session_cache = {}
        ppath = str(self.project_path)
        if ppath not in session_cache:
            return []
        file_cursors = [_convert_str_filecursor(fc) for fc in session_cache[ppath]]
        filestr = "\n".join(f"  {f}" for f in file_cursors)
        logger.info(f"Session {self.project_path} cached files:\n{filestr}")
        return file_cursors

    def save_file_cursors(self, file_cursors: list[FileCursor]):
        """Cache files and cursor positions for this session."""
        if self.__file_mode:
            logger.info("Skipping caching session files for single-file mode.")
            return
        filestr = "\n".join(f"  {f}" for f in file_cursors)
        logger.info(f"Session {self.project_path} caching files:\n{filestr}")
        file_cursors = [_convert_filecursor_str(fc) for fc in file_cursors]
        # Find and add existing entries from cache
        if SESSION_FILES_CACHE.exists():
            session_cache = json.loads(file_load(SESSION_FILES_CACHE))
        else:
            session_cache = {}
        path = str(self.project_path)
        existing_file_cursors = session_cache.get(path, [])
        if len(existing_file_cursors) > len(file_cursors):
            file_cursors += existing_file_cursors[len(file_cursors):]
        # Save to cache
        session_cache[path] = file_cursors
        file_dump(SESSION_FILES_CACHE, json.dumps(session_cache, indent=4))

    def repr_full_path(
        self,
        p: Path,
        /,
        *,
        to_project: bool = True,
        include_icon: bool = True,
    ) -> str:
        p = p.expanduser().resolve()
        icon = f"{self.get_path_icon(p)} " if include_icon else ""
        ppath = self.project_path
        if p.is_relative_to(USER_DIR):
            return f"{icon}{_Prefixes.config}/{_relative_without_empty(p, USER_DIR)}"
        for prefixed_path, replacement in _Prefixes.paths:
            if to_project and ppath.is_relative_to(prefixed_path):
                # Skip and prefer more direct relative path (project path)
                continue
            if p.is_relative_to(prefixed_path):
                return (
                    f"{icon}{replacement}/"
                    f"{_relative_without_empty(p, prefixed_path)}"
                )
        if to_project and p.is_relative_to(ppath):
            return f"{icon}{_Prefixes.proj}/{_relative_without_empty(p, ppath)}"
        if p.is_relative_to(Path.home()):
            return f"{icon}{_Prefixes.home}/{_relative_without_empty(p, Path.home())}"
        return str(p)

    @staticmethod
    def get_path_icon(p: Path, /) -> str:
        if ".git" in p.name:
            return ""
        if "LICENSE" in p.name:
            return ""
        if p.is_dir():
            return "" if p == Path.home() else ""
        return FILE_TYPE_ICONS.get(p.suffix, "")


def _relative_without_empty(p: Path, relative: Path) -> str:
    if p == relative:
        return ""
    return str(p.relative_to(relative))


def _convert_str_filecursor(s: str) -> FileCursor:
    if "::" not in s:
        return FileCursor(Path(s))
    sep_index = s.rfind("::")
    file, cursor = s[:sep_index], s[sep_index + 2:]
    cursor = tuple(int(c) for c in cursor.split(","))
    return FileCursor(Path(file), cursor)


def _convert_filecursor_str(fc: FileCursor) -> str:
    return f"{fc.file}::{fc.cursor[0]},{fc.cursor[1]}"


def _format_object(script: Script, obj: Name) -> str:
    assert isinstance(script, Script)
    assert isinstance(obj, Name)
    strs = [
        _format_object_short(script, obj),
        obj.docstring(),
    ]
    return "\n".join(strs)


def _format_object_short(script: Script, obj: Name) -> str:
    assert isinstance(script, Script)
    assert isinstance(obj, Name)
    name = obj.full_name or obj.description
    if obj.type in {"param"}:
        name = obj.description
    filename = obj.module_path
    filename = filename.name if filename else "NOPATH"
    return f"{name} ({filename} :: {obj.line},{obj.column})"


def _format_syntax_error(err) -> str:
    start = f"{err.line},{err.column}"
    end = f"{err.until_line},{err.until_column}"
    return f"{start} to {end} :: {err.get_message()}"


def _format_object_debug(obj: Name) -> str:
    strs = [f"[u]{obj!r}[/u]"]
    for attr in dir(obj):
        if attr.startswith("_"):
            continue
        value = getattr(obj, attr)
        keyname = attr[:18]
        if callable(value):
            keyname = f"{keyname}()"
            try:
                value = value()
            except Exception:
                value = f"failed call: {value}"
        value = repr(value)[:50]
        strs.append(f"  {keyname:<20} {value}")
    return "\n".join(strs)


def _title_break(text: str) -> str:
    text = f"  {text}  "
    return f"\n{text:≡^50}\n"
