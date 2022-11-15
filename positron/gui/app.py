"""GUI app."""

from loguru import logger
from . import kex as kx
from .editor.container import Container as EditorContainer
from ..util.file import open_path, USER_DIR, PROJ_DIR
from ..util import settings


WINDOW_TITLE_REFRESH_FPS = 10
WINDOW_SIZE = settings.get("window.size")
WINDOW_POS = settings.get("window.offset")
START_MAXIMIZED = settings.get("window.maximize")


class App(kx.App):
    def __init__(self, session):
        logger.info("Starting GUI.")
        super().__init__()
        self.icon = str(PROJ_DIR / "icon.png")
        self.__cleaned_up = False
        self._init_window()
        self.session = session
        self._project_path_repr = self.session.repr_full_path(
            self.session.project_path,
            to_project=False,
        )
        self.panels = EditorContainer(session)
        self.root.add(self.panels)
        self.im = kx.InputManager(
            name="App root",
            logger=logger.debug,
            log_press=settings.get("debug.hotkeys.press"),
            log_release=settings.get("debug.hotkeys.release"),
        )
        self.register_hotkeys()
        self.hook(self.update, WINDOW_TITLE_REFRESH_FPS)
        self.bind(current_focus=self._debug_focus)
        for n in (
            "debug.hotkeys.press",
            "debug.hotkeys.release",
            "window.border",
        ):
            settings.bind(n, self._update_settings)
        logger.info("Finished initialization.")

    def _update_settings(self, *args):
        logger.debug("App updating settings")
        self.im.log_press = settings.get("debug.hotkeys.press")
        self.im.log_release = settings.get("debug.hotkeys.release")
        kx.Window.toggle_borderless(not settings.get("window.border"))

    def _debug_focus(self, w, focus):
        logger.debug(f"{focus=}")

    def _init_window(self):
        kx.Window.toggle_borderless(not settings.get("window.border"))
        kx.schedule_once(lambda _: kx.Window.set_size(*WINDOW_SIZE))
        if any(c >= 0 for c in WINDOW_POS):
            kx.schedule_once(lambda _: kx.Window.set_position(*WINDOW_POS))
        if START_MAXIMIZED:
            kx.schedule_once(kx.Window.maximize)

    def _open_project_dir(self):
        open_path(self.session.project_path)

    def on_stop(self):
        if self.__cleaned_up:
            return
        self.__cleaned_up = True
        self.panels.clean_up()

    def register_hotkeys(self):
        self.im.remove_all()
        for args in [
            ("app.quit", self.stop, "^+ q"),
            ("app.restart", self.restart, "^+ w"),
            ("Reload settings", settings.load, "^+ f5", False, False),
            ("Open user dir", lambda: open_path(USER_DIR), "f12"),
            ("Open session dir", self._open_project_dir, "f9"),
            ("Debug hotkeys", self._debug_hotkeys, "^!+ f15"),
        ]:
            self.im.register(*args)

    def update(self, dt: float):
        winsize = f"{kx.Window.kivy.width}×{kx.Window.kivy.height}"
        self.title = f"Positron :: {self._project_path_repr} :: {winsize}"

    def _debug_hotkeys(self, *args):
        strs = [
            "All hotkeys:",
            *sorted(repr(kc) for kc in self.im.get_all_hotkeys()),
        ]
        logger.debug("\n".join(strs))
        settings.debug_bindings()
