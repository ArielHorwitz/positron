"""GUI app."""

from loguru import logger
from pathlib import Path
from positron.analyze.session import Session
from . import kex as kx, UI_LINE_HEIGHT, UI_CHAR_WIDTH, UI_FONT_KW
from .editor.container import Container as EditorContainer
from ..util.file import open_path, USER_DIR, PROJ_DIR
from ..util import settings


WINDOW_TITLE_REFRESH_FPS = 10
WINDOW_SIZE = settings.get("window.size")
WINDOW_POS = settings.get("window.offset")
START_MAXIMIZED = settings.get("window.maximize")


class App(kx.App):
    def __init__(self, project_path: Path):
        logger.info("Initializing GUI.")
        super().__init__()
        self.title = "Positron loading..."
        self.icon = str(PROJ_DIR / "icon.png")
        self.__project_path = project_path
        p = project_path.expanduser().resolve()
        loading_title = f" [u]Loading:[/u] [i]{p}[/i]"
        line_width = max(40, len(loading_title) + 4)
        loading_win_size = UI_CHAR_WIDTH * line_width, UI_LINE_HEIGHT * 7
        kx.Window.set_size(*loading_win_size)
        self._loading_label = kx.Label(
            halign="left",
            valign="top",
            **UI_FONT_KW,
            text=f"{loading_title}\n Indexing project...",
            color=(0.9, 0.2, 1),
        )
        self._loading_label.set_size(
            x=loading_win_size[0] - (UI_CHAR_WIDTH * 2),
            y=loading_win_size[1] - (UI_LINE_HEIGHT / 2),
        )
        self.root.make_bg(kx.get_color("purple", v=0.3))
        self.root.add(self._loading_label)
        kx.schedule_once(self._init_session, 1)

    def _init_session(self, *args):
        logger.info("Creating session...")
        self.session = Session(self.__project_path)
        self._loading_label.text += "\nﰪ Creating widgets..."
        kx.schedule_once(self._init_widgets)

    def _init_widgets(self, *args):
        logger.info("Initializing widgets...")
        self.__cleaned_up = False
        self._project_path_repr = self.session.repr_full_path(
            self.session.project_path,
            to_project=False,
            include_icon=False,
        )
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
        self._loading_label.text += "\n Opening editors..."
        kx.schedule_once(self._init_panels)

    def _init_panels(self, *args):
        logger.info("Initializing panels...")
        self.panels = EditorContainer(self.session)
        kx.Window.toggle_borderless(not settings.get("window.border"))
        self._loading_label.text += "\n Configuring window..."
        kx.schedule_once(self._init_window)

    def _init_window(self, *args):
        logger.info("Initializing window...")
        if any(c >= 0 for c in WINDOW_POS):
            kx.Window.set_position(*WINDOW_POS)
        kx.Window.set_size(*WINDOW_SIZE)
        kx.schedule_once(self._init_window2)

    def _init_window2(self, *args):
        if START_MAXIMIZED:
            kx.Window.maximize()
        self._loading_label.text += "\n拓 Assembling GUI..."
        kx.schedule_once(self._finalize_init)

    def _finalize_init(self, *args):
        self.root.clear_widgets()
        self.root.add(self.panels)
        del self._loading_label
        logger.info("Finished initialization.")

    def _update_settings(self, *args):
        logger.debug("App updating settings")
        self.im.log_press = settings.get("debug.hotkeys.press")
        self.im.log_release = settings.get("debug.hotkeys.release")
        kx.Window.toggle_borderless(not settings.get("window.border"))

    def _debug_focus(self, w, focus):
        logger.debug(f"{focus=}")

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
