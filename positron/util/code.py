"""Code related classes and utilities."""

from dataclasses import dataclass


@dataclass
class CodeError:
    message: str
    line: int
    column: int
