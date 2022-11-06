"""Settings module.

The user settings file from the home directory will be autogenerated with all the
builtin defaults if it does not exist. Each setting may be modified or even removed.

Settings may be loaded using a list of settings files which will take priority over
the user settings and defaults, e.g. by passing them as arguments in command line.

All settings files are configured using TOML.
"""


from loguru import logger
from typing import Optional, Any, Iterator
from pathlib import Path
import shutil
from .file import USER_DIR, PROJ_DIR, toml_load


SETTINGS_FILE = USER_DIR / "settings.toml"
DEFAULT_SETTINGS_FILE = PROJ_DIR / "positron" / "default_settings.toml"


def _yield_flat_dict(
    d: dict,
    path: Optional[list[str]] = None,
) -> Iterator[tuple[str, Any]]:
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


def _ensure_files():
    assert DEFAULT_SETTINGS_FILE.is_file()
    if not SETTINGS_FILE.is_file():
        shutil.copy(DEFAULT_SETTINGS_FILE, SETTINGS_FILE)


def _load_settings(settings_files: Optional[list[Path]] = None) -> dict[str, Any]:
    """Load settings from a list of settings files.

    See module documentation for details.
    """
    _ensure_files()
    if settings_files is None:
        settings_files = []
    settings_files.append(SETTINGS_FILE)
    # Collect settings
    defaults = _flatten_dict(toml_load(DEFAULT_SETTINGS_FILE))
    custom_settings = {}
    for file in settings_files:
        file_settings = _flatten_dict(toml_load(file))
        for name, value in file_settings.items():
            if name not in defaults:
                logger.warning(f"Unknown setting: {name}")
                continue
            if name in custom_settings:
                continue
            custom_settings[name] = value
    return defaults | custom_settings


class _Settings:
    _SETTINGS = None

    @classmethod
    def load(cls, settings_files: Optional[list[Path]] = None):
        """Reload settings with a given list of settings files.

        See module documentation for details.
        """
        logger.info(f"Loading settings with: {settings_files=}")
        cls._SETTINGS = _load_settings(settings_files)

    @classmethod
    def get(cls, setting_name: str) -> Any:
        """Get the value of *setting_name*."""
        try:
            return cls._SETTINGS[setting_name]
        except TypeError:
            raise RuntimeError("Settings uninitialized")
        except ValueError:
            raise ValueError(f"Unknown setting: {setting_name}")


_Settings.load()
load = _Settings.load
get = _Settings.get
