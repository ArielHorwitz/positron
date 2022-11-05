"""Snippets utilities."""

from typing import Iterable
import shutil
from itertools import islice
from dataclasses import dataclass
import fuzzysearch
import fuzzysearch.common
from .file import PROJ_DIR, USER_DIR, toml_load


MAX_RESULTS = 20


@dataclass
class Snippet:
    """A snippet is a piece of text to be entered, with cursor and selection control."""
    name: str
    """Snippet name."""
    text: str
    """Text to be inserted."""
    move: int = 0
    """Move cursor backwards after inserting text. Set negative to move to beginning."""
    select: int = 0
    """Select text backwards after moving cursor. Set negative to select all."""


def _load_snippets() -> dict[str, Snippet]:
    snippets_file = USER_DIR / "snippets.toml"
    if not snippets_file.exists():
        defaults_file = PROJ_DIR / "positron" / "default_snippets.toml"
        shutil.copy(defaults_file, snippets_file)
    user_snippets = toml_load(snippets_file)
    return {k: Snippet(k, **v) for k, v in user_snippets.items()}


SNIPPETS = _load_snippets()


def _fuzzy_search(pattern: str, text: str) -> list[fuzzysearch.common.Match]:
    return fuzzysearch.find_near_matches(
        pattern,
        text,
        max_l_dist=10,
        max_deletions=0,
        max_insertions=10,
        max_substitutions=0,
    )


def find_snippets(pattern: str, max_results: int = MAX_RESULTS) -> Iterable[Snippet]:
    """Snippets matching fuzzy search of pattern."""
    if not pattern:
        return list(SNIPPETS.values())
    filtered_snippets = (s for s in SNIPPETS.values() if _fuzzy_search(pattern, s.name))
    return islice(filtered_snippets, max_results)
