"""Linter utilities."""

from loguru import logger
from pathlib import Path
import traceback
import subprocess
from ..util.file import file_dump, CACHE_DIR
from ..util.code import CodeError
from ..util import settings


LINTER_CACHED_FILE = CACHE_DIR / "linter_cache.py"
FILE_STR = str(LINTER_CACHED_FILE)
FILE_STR_LEN = len(FILE_STR) + 1  # Include the ":" after the file name


class _Linter:
    flake8_args = tuple()

    @classmethod
    def _update_settings(cls, *args):
        cls.flake8_args = (
            "--extend-exclude",
            ",".join(settings.get("linter.exclude")),
            "--extend-ignore",
            settings.get("linter.ignore"),
            "--max-line-length",
            str(settings.get("linter.max_line_length")),
            "--max-complexity",
            str(settings.get("linter.max_complexity")),
            "--docstring-convention",
            settings.get("linter.docstring_convention"),
        )


# Bind settings
for n in filter(lambda x: x.startswith("linter."), settings.get_names()):
    settings.bind(n, _Linter._update_settings)
_Linter._update_settings()


def lint_path(path: Path, *, capture_output: bool = True) -> str:
    """Run flake8 on a path."""
    command_args = [
        "python",
        "-m",
        "flake8",
        str(path),
        *_Linter.flake8_args,
    ]
    if not capture_output:
        return subprocess.run(command_args)
    r = subprocess.run(command_args, capture_output=True, text=True)
    if r.stderr:
        return r.stderr
    return r.stdout


def lint_text(code: str, *args, **kwargs) -> list[CodeError]:
    """Run flake8 on a piece of unsaved code."""
    file_dump(LINTER_CACHED_FILE, code)
    try:
        r = lint_path(LINTER_CACHED_FILE, *args, **kwargs)
    except Exception as e:
        logger.warning("".join(traceback.format_exception(e)))
        logger.warning("Failed to run linter, see traceback above.")
        return []
    LINTER_CACHED_FILE.unlink()
    results = []
    append = results.append
    for line in r.split("\n"):
        if not line:
            continue
        if not line.startswith(FILE_STR):
            logger.warning(f"Unexpected line in linter: {line!r}")
            continue
        line, col, error = line[FILE_STR_LEN:].split(":", 2)
        error = error[1:]  # Leading whitespace
        try:
            # Errors are off by 1 column, I think...?
            line, col = int(line), max(0, int(col) - 1)
        except ValueError:
            logger.warning(f"Unexpected format from linter output: {line!r}")
            continue
        append(CodeError(error, line, col))
    return results
