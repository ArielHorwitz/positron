"""GUI app."""

from pathlib import Path
from . import kex as kx, FONTS_DIR
from .panels import PanelContainer
from ..util.file import open_path, USER_DIR, PROJ_DIR
from ..util import settings


FPS = settings.get("window.fps")
WINDOW_SIZE = settings.get("window.size")
WINDOW_POS = settings.get("window.offset")
START_MAXIMIZED = settings.get("window.maximize")
FONT = str(FONTS_DIR / settings.get("ui.font"))
UI_FONT_SIZE = settings.get("ui.font_size")


class App(kx.App):
    def __init__(self, session):
        print("Starting GUI.")
        super().__init__()
        self.icon = str(PROJ_DIR / "icon.png")
        self.__cleaned_up = False
        self._init_window()
        self.session = session
        self.im = kx.InputManager(name="App root")
        self.panels = PanelContainer(session)
        self.root.add(self.panels)
        self.register_hotkeys()
        self.hook(self.update, FPS)
        print("Finished initialization.")

    def _init_window(self):
        kx.Window.set_size(*WINDOW_SIZE)
        if any(c >= 0 for c in WINDOW_POS):
            kx.Window.set_position(*WINDOW_POS)
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
        for a, c, hk in [
            ("app.quit", self.stop, "^+ q"),
            ("app.restart", self.restart, "^+ w"),
            ("Open user dir", lambda: open_path(USER_DIR), "f9"),
            ("Open session dir", self._open_project_dir, "^+ f"),
        ]:
            self.im.register(a, c, hk)

    def update(self, dt: float):
        winsize = f"{kx.Window.kivy.width}×{kx.Window.kivy.height}"
        self.title = f"NIDE :: {self.session.project_path} :: {winsize}"
