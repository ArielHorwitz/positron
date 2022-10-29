"""Formatting for code analysis."""

from jedi import Script
from jedi.api.classes import Name


def format_object(script: Script, obj: Name) -> str:
    assert isinstance(script, Script)
    assert isinstance(obj, Name)
    strs = [
        format_object_short(script, obj),
        obj.docstring(),
    ]
    return "\n".join(strs)


def format_object_short(script: Script, obj: Name) -> str:
    assert isinstance(script, Script)
    assert isinstance(obj, Name)
    name = obj.full_name or obj.description
    if obj.type in {"param"}:
        name = obj.description
    filename = obj.module_path
    filename = filename.name if filename else "NOPATH"
    return f"{name} ({filename} :: {obj.line},{obj.column})"


def format_syntax_error(err) -> str:
    start = f"{err.line},{err.column}"
    end = f"{err.until_line},{err.until_column}"
    return f"{start} to {end} :: {err.get_message()}"


def format_object_debug(obj: Name) -> str:
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
