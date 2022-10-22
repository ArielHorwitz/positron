"""Settings module.

Settings are configured using TOML. A built-in default config exists in the
package, and a user-defined custom config exists in the usr dir. User-defined
values take priority.
"""
from typing import Any, Iterator
import copy
import shutil
import tomli
from . import file
from pathlib import Path


def _yield_flat_dict(d: dict, path=None) -> Iterator[tuple[str, Any]]:
    """Yield a '.' separated path and value in a nested dict."""
    path = [] if path is None else path
    for k, v in d.items():
        assert isinstance(k, str)
        new_path = [*path, k]
        if isinstance(v, dict):
            yield from _yield_flat_dict(v, path=new_path)
        else:
            yield ".".join(new_path), v


def _flatten_dict(d: dict) -> dict[str, Any]:
    """Return a flat dict given a nested dict, assuming all keys are strings."""
    return {path: value for path, value in _yield_flat_dict(d)}


def _load_settings() -> dict[str, Any]:
    # Resolve paths
    defaults_file = Path.cwd() / "nide" / "default_settings.toml"
    settings_file = file.USER_DIR / "settings.toml"
    # Create missing
    assert defaults_file.is_file()
    if not settings_file.is_file():
        shutil.copy(defaults_file, settings_file)
    # Read TOMLs
    defaults = _flatten_dict(file.toml_load(defaults_file))
    settings = _flatten_dict(file.toml_load(settings_file))
    non_redundant = {}
    for k, v in settings.items():
        if k not in defaults:
            print(f"Unknown setting: {k}")
            continue
        non_redundant[k] = v
    return defaults | non_redundant


__SETTINGS = _load_settings()


def get(setting_name: str) -> Any:
    """Get the value of *setting_name*."""
    return __SETTINGS[setting_name]
