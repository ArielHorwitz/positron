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
from typing import Optional, Any, Iterator, Iterable, Callable, NamedTuple
import functools
import weakref
from collections import defaultdict
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
shutil.copy(DEFAULT_SETTINGS_FILE, SETTINGS_DIR / "settings-defaults.toml")
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


SettingsDict = dict[str, Any]
"""A dictionary of settings."""
SettingsCallback = Callable[[str, Any, Any], None]
"""A function designed to be called when settings are changed.

Should accept as parameters: setting name, old value, and new value.
"""


class WeakCallable(NamedTuple):
    function: Callable
    bound_to: Optional[Any]


class WeakCallableList:
    """A list of weak references to bound/unbound functions.

    Solution for weakreffing bound methods: https://stackoverflow.com/a/21941670
    """

    def __init__(self):
        self._funcs = []

    def add(self, callback: Callable):
        """Add a weak reference to a bound/unbound function."""
        assert callable(callback)
        try:  # Handle methods as functions bounded to objects
            func = weakref.ref(callback.__func__)  # function
            bound_to = weakref.ref(callback.__self__)  # "self" or "cls" of the method
        except AttributeError:  # Normal unbound function
            func = weakref.ref(callback)
            bound_to = None
        self._funcs.append(WeakCallable(func, bound_to))

    def get_all(self):
        """Get all existing functions."""
        dead_refs = set()
        for wc in self._funcs:
            func, bound_ref = wc[0](), wc[1]
            # Normal unbound function
            if bound_ref is None:
                if func is None:
                    # Funcion no longer exists
                    dead_refs.add(wc)
                    continue
                yield func
            # Bound method
            else:
                bound_to = bound_ref()  # The "self" or "cls" of the method
                if bound_to is None:
                    # Method's bounded instance no longer exists
                    dead_refs.add(wc)
                    continue
                yield functools.partial(func, bound_to)
        for dead_ref in dead_refs:
            self._funcs.remove(dead_ref)


class _Settings:
    _LOADED_NAMES: Optional[tuple[str, ...]] = None
    _SETTINGS: Optional[dict[str, Any]] = None
    _BINDINGS: dict[str, WeakCallableList] = defaultdict(WeakCallableList)
    _USED_SETTINGS: set[str] = set()

    @classmethod
    def load(cls, file_names: Optional[list[str]] = None, /):
        """Reload settings with a given list of settings file names.

        See module documentation for more details.

        If no arguments are passed, the last names that were used are used again.
        """
        if file_names is None:
            file_names = cls._LOADED_NAMES
        cls._LOADED_NAMES = tuple(file_names) if file_names else tuple()
        settings_files = []
        for file_name in file_names:
            f = Path(file_name)
            if not f.is_file():
                f = SETTINGS_DIR / f"settings-{file_name}.toml"
            if not f.is_file():
                raise FileNotFoundError(f"Unknown settings name: {f}")
            settings_files.append(f)
        logger.info(f"Loading settings with: {settings_files=}")
        old_settings = cls._SETTINGS
        cls._SETTINGS = new_settings = _load_settings(settings_files)
        if old_settings is not None:
            cls._handle_changes(old_settings, new_settings)

    @classmethod
    def get(cls, name: str, /) -> Any:
        """Get the value of settings by name."""
        try:
            cls._USED_SETTINGS.add(name)
            return cls._SETTINGS[name]
        except TypeError:
            raise RuntimeError("Settings uninitialized")
        except ValueError:
            raise ValueError(f"Unknown setting: {name}")

    @classmethod
    def bind(cls, name: str, callback: SettingsCallback, /) -> Any:
        """Bind a callback to changes in settings. Returns the current value.

        Only WeakRefs are stored. Make sure to keep your callbacks from being grabage
        collected.
        Bounded callbacks are not called when the settings are first loaded, only when
        they are changed via reloading.
        """
        logger.debug(f"Binding setting {name!r} to {callback=}")
        current_value = cls.get(name)
        cls._BINDINGS[name].add(callback)
        return current_value

    @classmethod
    def bind_many(cls, callback: SettingsCallback, names: Iterable[str], /):
        """Bind each name with the callback."""
        for name in names:
            cls.bind(name, callback)

    @classmethod
    def get_unused(cls) -> list[str]:
        """List of settings names whose values were not yet requested."""
        return [s for s in cls._SETTINGS.keys() if s not in cls._USED_SETTINGS]

    @classmethod
    def _handle_changes(cls, old_settings: SettingsDict, new_settings: SettingsDict, /):
        assert set(old_settings.keys()) == set(new_settings.keys())
        for name, old_value in old_settings.items():
            new_value = new_settings[name]
            if old_value != new_value:
                logger.debug(f"Setting {name}: {old_value!r} -> {new_value!r}")
                callbacks = tuple(cls._BINDINGS[name].get_all())
                if not callbacks:
                    logger.debug("No callbacks for settings change.")
                for func in callbacks:
                    logger.debug(f"Calling: {func.func} {func.args}")
                    func(name, old_value, new_value)

    @classmethod
    def get_names(cls):
        return cls._SETTINGS.keys()

    @classmethod
    def debug_bindings(cls):
        nl = "\n"
        d = "\n".join((
            f"{name}:\n{nl.join(f'    - {c}' for c in funcset.get_all())}"
            for name, funcset in cls._BINDINGS.items()
        ))
        logger.debug(f"All bindings:\n{d}")


load = _Settings.load
get = _Settings.get
bind = _Settings.bind
get_names = _Settings.get_names
unused = _Settings.get_unused
debug_bindings = _Settings.debug_bindings
