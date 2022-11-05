"""Project session for analysis."""

from typing import Optional
from itertools import islice
from pathlib import Path
import re
import json
import jedi
from jedi import Script
from jedi.api.classes import Name
from ..util.file import file_load, file_dump, USER_DIR, FileCursor
from ..util.code import CodeError
from .linter import lint_text


SESSION_FILES_CACHE = USER_DIR / "session_cache.json"
SESSION_FILES_CACHE.parent.mkdir(parents=True, exist_ok=True)
if not SESSION_FILES_CACHE.exists():
    file_dump(SESSION_FILES_CACHE, "{}")
RE_TRAILING_WHITESPACE = re.compile(r"( +)\n")
RE_NEWLINE = re.compile(r"\n")


def _title_break(text: str) -> str:
    text = f"  {text}  "
    return f"\n{text:≡^50}\n"


class Session:
    def __init__(self, project_path: Path, env_path: Optional[Path] = None):
        self.__file_mode = None
        if not project_path.is_dir():
            self.__file_mode = project_path
            project_path = project_path.parent
        self.project_path = project_path.expanduser().resolve()
        if env_path is None:
            all_venvs = list(jedi.find_virtualenvs(paths=[project_path]))
            print("Available environments:")
            print("\n".join(f"  {v.executable}" for v in all_venvs))
            env_path = all_venvs[-1].executable
        self.env_path = Path(env_path)
        self._project = jedi.Project(project_path, environment_path=env_path)
        print(f"Created project:     {project_path}")
        print(f"Project environment: {env_path}")

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
            print(f"get_completions exception: {e}")
            return []
        return islice(completions, max_completions)

    def get_context(self, path: Path, code: str, line: int, col: int):
        script = jedi.Script(code=code, path=path, project=self._project)
        return script.get_context(line, col)

    def get_info(self, path: Path, code: str, line: int, col: int) -> str:
        """Multiline string of code analysis under the cursor."""
        print(f"Getting info for: {path} :: {line},{col}")
        script = jedi.Script(code=code, path=path, project=self._project)
        debug_strs = []
        strs = []
        append = strs.append
        extend = strs.extend

        # Syntax errors
        syntax_errors = script.get_syntax_errors()
        if syntax_errors:
            append(_title_break("Syntax Errors"))
            extend(_format_syntax_error(err) for err in syntax_errors)

        # Definitions
        append(_title_break("Definitions"))
        names = list(script.help(line, col))
        if names:
            append("\n==========\n".join(_format_object(script, n) for n in names))
            debug_strs.append(_format_object_debug(names[0]))
        else:
            append("No definitions found.")

        # References
        append(_title_break("References"))
        refs = list(script.get_references(line, col))
        if refs:
            extend(_format_object_short(script, r) for r in refs)
        else:
            append("No references found.")

        # Context
        append(_title_break("Context"))
        context = script.get_context(line, col)
        append(_format_object_short(script, context))

        # Code completion
        completions = script.complete(line, col)
        if completions:
            append(_title_break("Code completions"))
            extend(
                f"{comp.name}  ¬{comp.complete}"
                for comp in islice(completions, 20)
            )

        # All module names
        append(_title_break("All definitions"))
        names = list(script.get_names(all_scopes=True))
        if names:
            extend(
                _format_object_short(script, n)
                for n in names
                if n.type in {"class", "function"}
            )
        else:
            append("No names found...")

        append(_title_break("Debug"))
        extend(debug_strs)

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
        if do_complete:
            yield from self._project.complete_search(string, all_scopes=exhaustive)
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
        session_cache = json.loads(file_load(SESSION_FILES_CACHE))
        ppath = str(self.project_path)
        if ppath not in session_cache:
            return []
        file_cursors = [_convert_str_filecursor(fc) for fc in session_cache[ppath]]
        filestr = "\n".join(f"  {f}" for f in file_cursors)
        print(f"Session {self.project_path} cached files:\n{filestr}")
        return file_cursors

    def save_file_cursors(self, file_cursors: list[FileCursor]):
        """Cache files and cursor positions for this session."""
        if self.__file_mode:
            print("Skipping caching session files for single-file mode.")
            return
        filestr = "\n".join(f"  {f}" for f in file_cursors)
        print(f"Session {self.project_path} caching files:\n{filestr}")
        file_cursors = [_convert_filecursor_str(fc) for fc in file_cursors]
        # Find and add existing entries from cache
        session_cache = json.loads(file_load(SESSION_FILES_CACHE))
        path = str(self.project_path)
        existing_file_cursors = session_cache.get(path, [])
        if len(existing_file_cursors) > len(file_cursors):
            file_cursors += existing_file_cursors[len(file_cursors):]
        # Save to cache
        session_cache[path] = file_cursors
        file_dump(SESSION_FILES_CACHE, json.dumps(session_cache, indent=4))


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
