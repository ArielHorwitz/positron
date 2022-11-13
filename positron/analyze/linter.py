"""Linter utilities."""

from loguru import logger
from pathlib import Path
import traceback
import subprocess
from ..util.file import file_dump, CACHE_DIR
from ..util.code import CodeError
from ..util import settings


EXTEND_EXCLUDE = ",".join(settings.get("linter.exclude"))
EXTEND_IGNORE = settings.get("linter.ignore")
MAX_LINE_LENGTH = settings.get("linter.max_line_length")
MAX_COMPLEXITY = settings.get("linter.max_complexity")
DOCSTRING_CONVENTION = settings.get("linter.docstring_convention")
LINTER_CACHED_FILE = CACHE_DIR / "linter_cache.py"
FILE_STR = str(LINTER_CACHED_FILE)
FILE_STR_LEN = len(FILE_STR) + 1  # Include the ":" after the file name


def lint_path(
    path: Path,
    max_line_length: int = MAX_LINE_LENGTH,
    max_complexity: int = MAX_COMPLEXITY,
    docstring_convention: str = DOCSTRING_CONVENTION,
    capture_output: bool = True,
) -> str:
    """Run flake8 on a path."""
    command_args = [
        "python",
        "-m",
        "flake8",
        str(path),
        "--extend-exclude",
        EXTEND_EXCLUDE,
        "--extend-ignore",
        EXTEND_IGNORE,
        "--max-line-length",
        str(max_line_length),
        "--max-complexity",
        str(max_complexity),
        "--docstring-convention",
        docstring_convention,
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
