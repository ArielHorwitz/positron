"""Settings module.

There exist two settings sources by default: the user settings file and the
internal defaults. Anything defined in the user settings file overrides the
defaults, and may even be left blank.

Settings must be loaded - optionally using a list of settings files which will
take priority over the user settings and defaults, e.g. by passing them as
arguments in command line.

All settings files are configured using TOML.
"""


from loguru import logger
from typing import Optional, Any, Iterator
from pathlib import Path
import shutil
from .file import SETTINGS_DIR, PROJ_DIR, toml_load, file_dump


SAMPLE_SETTINGS = """# This is your settings file.
# Anything placed here will override the defaults. To see all available
# settings, browse "#/settings/defaults.toml".
# Settings files use TOML - https://toml.io
"""

SETTINGS_FILE = SETTINGS_DIR / "settings.toml"
DEFAULT_SETTINGS_FILE = PROJ_DIR / "positron" / "default_settings.toml"
shutil.copy(DEFAULT_SETTINGS_FILE, SETTINGS_DIR / "defaults.toml")
if not SETTINGS_FILE.exists():
    file_dump(SETTINGS_FILE, SAMPLE_SETTINGS)


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


def _load_settings(settings_files: Optional[list[Path]] = None) -> dict[str, Any]:
    """Load settings from a list of settings files.

    See module documentation for details.
    """
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
    def load(cls, settings_names: Optional[list[str]] = None, /):
        """Reload settings with a given list of settings file names.

        See module documentation for details.
        """
        if not settings_names:
            cls._SETTINGS = _load_settings()
            return

        settings_files = []
        for settings_name in settings_names:
            f = Path(settings_name)
            if not f.is_file():
                f = SETTINGS_DIR / f"settings-{settings_name}.toml"
            if not f.is_file():
                raise FileNotFoundError(f"Unknown settings name: {f}")
            settings_files.append(f)
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


load = _Settings.load
get = _Settings.get
