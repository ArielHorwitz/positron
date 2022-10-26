"""CLI for testing the prototype."""

from typing import Optional
from pathlib import Path
import json
from .file import USER_DIR, file_dump, file_load
import jedi
from jedi.api.classes import Name, Signature


SESSION_FILES_CACHE = USER_DIR / "session_cache.json"
SESSION_FILES_CACHE.parent.mkdir(parents=True, exist_ok=True)
if not SESSION_FILES_CACHE.exists():
    file_dump(SESSION_FILES_CACHE, "{}")


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
        files_cache[str(self.project_path)] = [str(f) for f in files]
        file_dump(SESSION_FILES_CACHE, json.dumps(files_cache, indent=4))

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

    def get_info(self, code: str, line: int, col: int) -> str:
        script = jedi.Script(code=code, project=self._project)
        strs = [f"Context: {script.get_context(line, col).full_name}"]
        # Names
        names = list(script.infer(line, col))
        strs.extend(self.get_info_name(name) for name in names)
        # Signatures
        signatures = list(script.get_signatures(line, col))
        strs.extend(self.get_info_sig(sig) for sig in signatures)
        # Sub definitions
        strs.extend(self.get_info_subdefs(name) for name in names)
        # References
        # references = list(script.get_references(line, col))
        # strs.append("References:")
        # strs.extend(self.get_info_name(name) for name in references)
        # Syntax errors
        syntax_errors = script.get_syntax_errors()
        strs.extend(f"{err}" for err in syntax_errors)
        return "\n\n".join(strs)

    def get_error_summary(self, code: str) -> str:
        script = jedi.Script(code=code, project=self._project)
        syntax_errors = script.get_syntax_errors()
        if not syntax_errors:
            return "No syntax errors."
        count = len(syntax_errors)
        first_error = syntax_errors[0]
        return f"{count} syntax errors [{first_error.line},{first_error.column}]"

    def get_info_name(self, name: Name) -> str:
        reference = "" if name.is_definition() else " REF"
        # try:
        #     type_hint = name.get_type_hint()
        # except NotImplementedError:
        #     type_hint = "unknown"
        path = name.module_path
        if path and path.is_relative_to(self.project_path):
            path = path.relative_to(self.project_path)
            path = Path("$PROJ") / path
        return "\n".join(
            [
                f"{name.full_name}",
                f"<{name.type}>{reference} ({path}::{name.line},{name.column})",
                # f"Type hint: {type_hint}",
                f"\n{name.docstring()}",
            ]
        )

    @staticmethod
    def get_info_sig(sig: Signature) -> str:
        return f"\n{sig.to_string()}"

    @staticmethod
    def get_info_subdefs(name: Name) -> str:
        subnames = name.defined_names()
        if not subnames:
            return ""
        subdefs = "\n".join(f"  - {sn.name}" for sn in subnames)
        return f"Subdefinitions:\n{subdefs}"
