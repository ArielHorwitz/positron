"""Code editor widget."""

from typing import Optional
import sys
import traceback
import arrow
from pathlib import Path
from .. import kex as kx, FONTS_DIR
from ... import settings
from ...session import Session


FONT = str(FONTS_DIR / settings.get("editor.font"))
FONT_SIZE = settings.get("editor.font_size")
UI_FONT_SIZE = settings.get("ui.font_size")
GUTTER_PADDING = settings.get("editor.gutter_padding")
DIR_TREE_DEPTH = settings.get("project.tree_depth")


class CodeEditor(kx.Box):
    def __init__(self, session: Session, file: Path = Path("__init__.py")):
        super().__init__(orientation="vertical")
        self.session = session
        self._current_file = file
        # Widgets
        self.im = kx.InputManager(
            default_controls=False,
            logger=kx.consume_args,
        )
        self.find_entry = kx.CodeEntry(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            on_text_validate=self.find_next,
            write_tab=False,
            style_name="solarized-dark",
            background_color=kx.XColor(0.6, 0.2, 1, v=0.2).rgba,
            multiline=False,
        )
        control_frame = kx.Box()
        control_frame.set_size(y=40)
        control_frame.add(self.find_entry)
        main_frame = kx.Box()
        self.code_entry = kx.CodeEntry(
            font_name=FONT,
            font_size=FONT_SIZE,
            do_wrap=False,
            style_name="one-dark",
            background_color=kx.XColor(0.7, 0.85, 1, v=0.075).rgba,
            scroll_distance=750,
        )
        self.code_entry.focus = True
        self.code_entry.bind(
            scroll_y=self._on_scroll,
            size=self._on_scroll,
            focus=self._on_focus,
            cursor=self._on_cursor,
            text=self._on_text,
        )
        line_gutter_top_padding = kx.Anchor()
        line_gutter_top_padding.set_size(y=GUTTER_PADDING)
        self.line_gutter = kx.Label(
            font_name=FONT,
            font_size=FONT_SIZE,
            valign="top",
            halign="right",
        )
        line_gutter_frame = kx.Box(orientation="vertical")
        line_gutter_frame.make_bg(kx.XColor(0.2, 1, 0.6, v=0.2))
        line_gutter_frame.set_size(x=50)
        line_gutter_frame.add(line_gutter_top_padding, self.line_gutter)
        main_frame.add(line_gutter_frame, self.code_entry)
        status_bar = kx.Box()
        status_bar.set_size(y=25, hx=0.95)
        self.status_left = kx.Label(font_name=FONT, font_size=14, halign="left")
        self.status_right = kx.Label(font_name=FONT, font_size=14, halign="right")
        status_bar.add(self.status_left, self.status_right)
        self.add(control_frame, main_frame, status_bar)
        # Controls
        for action, callback, hotkey in [
            ("Load", self.load, "^ l"),
            ("Save", self.save, "^ s"),
            ("Analyze", self.analyze, "^+ a"),
            ("Find", self.find_entry.set_focus, "^ f"),
            ("Find next", self.find_next, "f3"),
            ("Find previous", self.find_prev, "+ f3"),
        ]:
            self.im.register(action, callback, hotkey)
        self.load()

    # File management
    def save(self, file: Optional[Path] = None):
        if file is None:
            file = self._current_file
        self._current_file = file
        self._on_cursor()
        file.parent.mkdir(parents=True, exist_ok=True)
        with open(file, "w", encoding="utf-8") as f:
            f.write(self.code_entry.text)
        ts = arrow.now().format("HH:mm:ss")
        print(f"Saved @ {ts} to: {file}")

    def load(self, file: Optional[Path] = None, reset_cursor: bool = True):
        if file is None:
            file = self._current_file
        self._current_file = file
        if not file.exists():
            print(f"New unsaved file: {file}")
            text = ""
        else:
            ts = arrow.now().format("HH:mm:ss")
            print(f"Loaded @ {ts} from: {file}")
            with open(file) as f:
                text = f.read()
        self.code_entry.text = text
        if reset_cursor:
            kx.schedule_once(self.code_entry.reset_cursor_selection, 0)

    # Cursor management
    @property
    def cursor(self):
        column, line = self.code_entry.cursor
        line += 1
        return line, column

    def cursor_full(self, sep: str = "::"):
        line, column = self.cursor
        path = self._current_file.relative_to(self.session.project_path)
        return f"{path}{sep}{line},{column}"

    # Code inspection
    def find_next(self, *args):
        self.code_entry.focus = True
        self.code_entry.find_next(self.find_entry.text)

    def find_prev(self, *args):
        self.code_entry.focus = True
        self.code_entry.find_prev(self.find_entry.text)

    def analyze(self, *a):
        code = self.code_entry.text
        try:
            info_str = self.session.get_info(code, *self.cursor)
        except Exception:
            tb = "".join(traceback.format_exception(*sys.exc_info()))
            info_str = f"Failed to retrieve info:\n{tb}"
        print(f"{self.cursor_full()}\n{info_str}")

    # Events
    def set_focus(self, *args):
        kx.schedule_once(self.code_entry.set_focus, 0)

    def _on_cursor(self, *a):
        self.status_right.text = self.cursor_full(" :: ")

    def _on_scroll(self, *a):
        start, finish = self.code_entry.get_line_range()
        finish = min(finish, len(self.code_entry._lines)+1)
        self.line_gutter.text = "\n".join(
            f"{i:>4}" for i in range(start, finish)
        )

    def _on_focus(self, w, focus):
        self.im.active = focus

    def _on_text(self, *a):
        error_summary = self.session.get_error_summary(self.code_entry.text)
        self.status_left.text = error_summary
        self._on_cursor()
        kx.schedule_once(self._on_scroll, 0)
