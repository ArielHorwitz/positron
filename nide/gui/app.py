"""GUI app."""

from . import kex as kx, FONTS_DIR
from .editor import CodeEditor
from ..session import Session
from ..file import open_path, USER_DIR, PROJ_DIR
from .. import settings


FPS = settings.get("window.fps")
WINDOW_SIZE = settings.get("window.size")
WINDOW_POS = settings.get("window.offset")
START_MAXIMIZED = settings.get("window.maximize")
PANEL_WIDTH = settings.get("ui.panel_width")
FONT = str(FONTS_DIR / settings.get("ui.font"))
UI_FONT_SIZE = settings.get("ui.font_size")
DEFAULT_FILES = settings.get("project.open")


class App(kx.App):
    def __init__(self, session: Session):
        print("Starting GUI.")
        super().__init__()
        self.icon = str(PROJ_DIR / "icon.png")
        self._init_window()
        self.session = session
        self.im = kx.InputManager(logger=kx.consume_args)
        self.build_widgets()
        self.hook(self.update, FPS)

    def _init_window(self):
        kx.Window.set_size(*WINDOW_SIZE)
        if any(c >= 0 for c in WINDOW_POS):
            kx.Window.set_position(*WINDOW_POS)
        if START_MAXIMIZED:
            kx.schedule_once(kx.Window.maximize)

    def build_widgets(self):
        self.root.clear_widgets()
        self.panel = kx.Label(
            halign="left",
            valign="top",
            fixed_width=True,
            font_name=FONT,
            font_size=UI_FONT_SIZE,
        )
        self.editors = [CodeEditor(self.session, file) for file in DEFAULT_FILES]
        panel_frame = kx.DBox()
        panel_frame.add(self.panel)
        self.panel_scroll = kx.Scroll(view=panel_frame)
        self.panel_scroll.set_size(x=PANEL_WIDTH)
        self.panel_scroll.make_bg(kx.get_color("cyan", v=0.2))
        main_frame = self.root.add(kx.Box())
        main_frame.add(self.panel_scroll, *self.editors)
        self.editors[0].set_focus()
        self.register_hotkeys()

    def register_hotkeys(self):
        self.im.remove_all()
        self.im.register_defaults()

        self.im.register(
            "Open user dir",
            lambda: open_path(USER_DIR),
            "^+ f",
        )

        for i, editor in enumerate(self.editors):
            self.im.register(
                f"Focus Editor {i+1}",
                editor.set_focus,
                f"^ {i+1}",
            )

        self.im.register(
            "Scroll panel up",
            self.panel_scroll.scroll_up,
            "^+ up",
            allow_repeat=True,
        )
        self.im.register(
            "Scroll panel down",
            self.panel_scroll.scroll_down,
            "^+ down",
            allow_repeat=True,
        )

    def update(self, dt: float):
        fps = round(1 / dt)
        winsize = f"{kx.Window.kivy.width},{kx.Window.kivy.height}"
        self.title = f"NIDE :: {self.session.project_path} :: {fps:>2} FPS :: {winsize}"

    def set_panel(self, text: str):
        self.panel.text = f"{text}"
