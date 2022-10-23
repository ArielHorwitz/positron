"""GUI app."""

from pathlib import Path
from . import kex as kx, FONTS_DIR
from .editor.editor import EditorPanel
from ..util.file import open_path, USER_DIR, PROJ_DIR
from ..util import settings


FPS = settings.get("window.fps")
WINDOW_SIZE = settings.get("window.size")
WINDOW_POS = settings.get("window.offset")
START_MAXIMIZED = settings.get("window.maximize")
FONT = str(FONTS_DIR / settings.get("ui.font"))
UI_FONT_SIZE = settings.get("ui.font_size")
EDITOR_COUNT = settings.get("ui.editors")
DEFAULT_FILES = settings.get("project.open")


class App(kx.App):
    def __init__(self, session):
        print("Starting GUI.")
        super().__init__()
        self.icon = str(PROJ_DIR / "icon.png")
        self._init_window()
        self.session = session
        self.im = kx.InputManager(name="App root")
        self.build_widgets()
        self.hook(self.update, FPS)
        print("Finished initialization.")

    def _init_window(self):
        kx.Window.set_size(*WINDOW_SIZE)
        if any(c >= 0 for c in WINDOW_POS):
            kx.Window.set_position(*WINDOW_POS)
        if START_MAXIMIZED:
            kx.schedule_once(kx.Window.maximize)

    def build_widgets(self):
        self.root.clear_widgets()
        files = [self.session.project_path / Path(file) for file in DEFAULT_FILES]
        editor_count = EDITOR_COUNT
        kw = {"cols": editor_count}
        if editor_count > 3:
            editor_count += editor_count % 2
            kw = {"rows": 2}
        self.editors = []
        for i in range(editor_count):
            file = files.pop(0) if files else None
            self.editors.append(EditorPanel(i, self.session, file))
        main_frame = kx.Grid(**kw)
        main_frame.add(*self.editors)
        self.root.add(main_frame)
        self.editors[0].set_focus()
        self.register_hotkeys()

    def register_hotkeys(self):
        self.im.remove_all()
        self.im.register("app.quit", self.stop, "^+ q")
        self.im.register("app.restart", self.restart, "^+ w")
        self.im.register(
            "Open user dir",
            lambda: open_path(USER_DIR),
            "f9",
        )
        for editor in self.editors:
            self.im.register(
                f"Focus Editor {editor.uid}",
                editor.set_focus,
                f"f{editor.uid+1}",
            )

    def update(self, dt: float):
        fps = round(1 / dt)
        winsize = f"{kx.Window.kivy.width},{kx.Window.kivy.height}"
        self.title = f"NIDE :: {self.session.project_path} :: {fps:>2} FPS :: {winsize}"
