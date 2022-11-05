"""Settings module.

Settings are configured using TOML. A built-in default config exists in the
package, and a user-defined custom config exists in the usr dir. User-defined
values take priority.
"""
from typing import Any, Iterator
import shutil
from . import file


SETTINGS_FILE = file.USER_DIR / "settings.toml"
DEFAULT_SETTINGS_FILE = file.PROJ_DIR / "positron" / "default_settings.toml"


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
    # Create missing
    assert DEFAULT_SETTINGS_FILE.is_file()
    if not SETTINGS_FILE.is_file():
        shutil.copy(DEFAULT_SETTINGS_FILE, SETTINGS_FILE)
    # Read TOMLs
    defaults = _flatten_dict(file.toml_load(DEFAULT_SETTINGS_FILE))
    settings = _flatten_dict(file.toml_load(SETTINGS_FILE))
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
