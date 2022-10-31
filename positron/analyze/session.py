"""Project session for analysis."""

from typing import Optional
from itertools import islice
from pathlib import Path
import json
import jedi
from jedi.api.classes import Name
from .formatting import (
    format_object,
    format_object_short,
    format_object_debug,
    format_syntax_error,
)
from ..util.file import file_load, file_dump, USER_DIR


SESSION_FILES_CACHE = USER_DIR / "session_cache.json"
SESSION_FILES_CACHE.parent.mkdir(parents=True, exist_ok=True)
if not SESSION_FILES_CACHE.exists():
    file_dump(SESSION_FILES_CACHE, "{}")


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
            print(f"Available environments:")
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
        ) -> list[str]:
        """List of strings to complete code under the cursor."""
        script = jedi.Script(code=code, path=path, project=self._project)
        completions = script.complete(line, col)
        return [c.complete for c in islice(completions, max_completions)]

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
            extend(format_syntax_error(err) for err in syntax_errors)

        # Definitions
        append(_title_break("Definitions"))
        names = list(script.help(line, col))
        if names:
            append("\n==========\n".join(format_object(script, n) for n in names))
            debug_strs.append(format_object_debug(names[0]))
        else:
            append("No definitions found.")

        # References
        append(_title_break("References"))
        refs = list(script.get_references(line, col))
        if refs:
            extend(format_object_short(script, r) for r in refs)
        else:
            append("No references found.")

        # Context
        append(_title_break("Context"))
        context = script.get_context(line, col)
        append(format_object_short(script, context))

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
                format_object_short(script, n)
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
        if do_complete:
            completions = self._project.complete_search(string)
            try:
                remainder = next(completions).complete
                string = f"{string}{remainder}"
            except StopIteration:
                return []
        results = self._project.search(string, all_scopes=exhaustive)
        return results

    def get_error_summary(self, code: str) -> str:
        script = jedi.Script(code=code, project=self._project)
        syntax_errors = script.get_syntax_errors()
        if not syntax_errors:
            return "No syntax errors."
        count = len(syntax_errors)
        first_error = syntax_errors[0]
        return f"{count} syntax errors [{first_error.line},{first_error.column}]"

    def get_session_files(self) -> list[Path]:
        """List of files opened for this session in cache."""
        if self.__file_mode:
            return [self.__file_mode]
        files_cache = json.loads(file_load(SESSION_FILES_CACHE))
        files = [Path(f) for f in files_cache.get(str(self.project_path), [])]
        filestr = "\n".join(f"  {f}" for f in files)
        print(f"Session {self.project_path} cached files:\n{filestr}")
        return files

    def save_session_files(self, files: list[Path]):
        """Cache list of open files for this session."""
        if self.__file_mode:
            print(f"Skipping caching session files for single-file mode.")
        filestr = "\n".join(f"  {f}" for f in files)
        print(f"Session {self.project_path} caching files:\n{filestr}")
        if SESSION_FILES_CACHE.exists():
            files_cache = json.loads(file_load(SESSION_FILES_CACHE))
        else:
            files_cache = {}
        path = str(self.project_path)
        existing_files = files_cache.get(path, [])
        if len(existing_files) > len(files):
            files += existing_files[len(files):]
        files_cache[path] = [str(f) for f in files]
        file_dump(SESSION_FILES_CACHE, json.dumps(files_cache, indent=4))
