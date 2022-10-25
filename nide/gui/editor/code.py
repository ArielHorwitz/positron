"""Code editor widget."""

from typing import Optional
import os.path
import sys
import traceback
import arrow
from pathlib import Path
from pygments.util import ClassNotFound as LexerClassNotFound
from pygments.styles import get_style_by_name, STYLE_MAP
from pygments.lexers import get_lexer_for_filename
from pygments.lexers.markup import MarkdownLexer
from .. import kex as kx, FONTS_DIR
from ...util import settings
from ...util.file import file_load, file_dump, try_relative, USER_DIR


STYLE_NAME = settings.get("editor.style")
print(f"Available styles: {list(STYLE_MAP.keys())}")
if STYLE_NAME not in STYLE_MAP:
    STYLE_NAME = "default"
print(f"Chosen style: {STYLE_NAME}")
FONT = str(FONTS_DIR / settings.get("editor.font"))
FONT_SIZE = settings.get("editor.font_size")
UI_FONT_SIZE = settings.get("ui.font_size")
AUTO_LOAD = settings.get("editor.auto_load")
GUTTER_PADDING = settings.get("editor.gutter_padding")
DISK_DIFF_INTERVAL = settings.get("editor.disk_diff_interval")


def timestamp():
    return arrow.now().format("HH:mm:ss")


class CodeEditor(kx.Box):
    def __init__(self, session, uid: int, file: Optional[Path] = None):
        super().__init__(orientation="vertical")
        self.session = session
        self.__uid = uid
        if file is None:
            file = USER_DIR / "settings.toml"
        self._current_file = file.expanduser().resolve()
        self.__disk_modified_time = None
        self.__disk_diff = False
        self.__disk_cache = None
        # Widgets
        self.im = kx.InputManager(name=f"Code editor {uid}")
        self.find_entry = kx.CodeEntry(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            on_text_validate=self.find_next,
            select_on_focus=True,
            write_tab=False,
            style_name="solarized-dark",
            background_color=kx.XColor(0.12, 0.04, 0.2).rgba,
            multiline=False,
        )
        control_frame = kx.Box()
        control_frame.set_size(y=40)
        control_frame.add(self.find_entry)
        main_frame = kx.Box()
        self.code_entry = kx.CodeEntry(
            font_name=FONT,
            font_size=FONT_SIZE,
            auto_indent=True,
            do_wrap=False,
            style_name=STYLE_NAME,
            background_color=kx.XColor(0.025, 0.045, 0.05).rgba,
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
        self.add(control_frame, status_bar, main_frame)
        # Controls
        for reg_args in [
            ("Open settings", self._open_settings, "f8"),
            ("Reload", self.reload, "^ l"),
            ("Save", self.save, "^ s"),
            ("Delete file", self.delete_file, "^+ delete"),
            ("Analyze", self.analyze, "^+ a"),
            ("Duplicate lines", self.code_entry.duplicate, "^+ d", True),
            ("Shift lines up", lambda: self.code_entry.shift_lines(-1), "!+ up", True),
            ("Shift lines down", lambda: self.code_entry.shift_lines(1), "!+ down", True),
            ("Find", self.find_entry.set_focus, "^ f"),
            ("Find next", self.find_next, "f3", True),
            ("Find previous", self.find_prev, "+ f3", True),
        ]:
            self.im.register(*reg_args)
        if AUTO_LOAD:
            self.load()
        kx.schedule_interval(self._check_disk_diff, DISK_DIFF_INTERVAL)

    # File management
    @property
    def file(self):
        return self._current_file

    def save(self, file: Optional[Path] = None):
        if file is None:
            file = self._current_file
        self._current_file = file
        text = self.code_entry.text
        file.parent.mkdir(parents=True, exist_ok=True)
        file_dump(file, text)
        print(f"Saved  @ {timestamp()} to: {file}")
        self.__disk_modified_time = self._get_disk_mod_date(self._current_file)
        self.__disk_cache = text
        self.__disk_diff = False
        self._on_cursor()

    def load(self, file: Optional[Path] = None, reset_cursor: bool = True):
        if file is None:
            file = self._current_file
        self._current_file = file
        self._update_lexer()
        text = self._get_disk_content(file)
        if text:
            print(f"Loaded @ {timestamp()} from: {file}")
        else:
            text = ""
            print(f"New unsaved file: {file}")
        self.__disk_modified_time = self._get_disk_mod_date(file)
        self.__disk_cache = text
        self.__disk_diff = False
        cursor = self.code_entry.cursor
        self.code_entry.text = text
        if reset_cursor:
            kx.schedule_once(self.code_entry.reset_cursor_selection)
        else:
            self.code_entry.cursor = cursor

    def reload(self, *args):
        self.load(reset_cursor=False)

    def delete_file(self):
        if self._current_file.exists():
            self._current_file.unlink()
            print(f"Deleted @ {timestamp()} file: {self._current_file}")
            self.load()

    def _get_disk_content(self, file: Path) -> str:
        if not file.exists():
            return None
        return file_load(file)

    def _get_disk_mod_date(self, file: Path):
        return os.path.getmtime(file) if file.exists() else None

    def _check_disk_diff(self, *args):
        if not self._current_file.exists():
            self.__disk_modified_time = None
            self.__disk_cache = None
            self.__disk_diff = True
        else:
            # Update disk cache if file has changed on disk
            modified_time = self._get_disk_mod_date(self._current_file)
            if modified_time != self.__disk_modified_time:
                self.__disk_cache = self._get_disk_content(self._current_file)
                self.__disk_modified_time = modified_time
                print(f"Cached @ {timestamp()} for: {self._current_file}")
            self.__disk_diff = self.__disk_cache != self.code_entry.text
        self._on_cursor()

    def _update_lexer(self):
        try:
            lexer = get_lexer_for_filename(self._current_file.name)
        except LexerClassNotFound:
            lexer = MarkdownLexer()
        self.code_entry.lexer = lexer

    def _open_settings(self):
        self.load(file=USER_DIR / "settings.toml")

    # Cursor management
    @property
    def cursor(self):
        column, line = self.code_entry.cursor
        line += 1
        return line, column

    def cursor_full(self, sep: str = "::"):
        line, column = self.cursor
        path = try_relative(self._current_file, self.session.project_path)
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
        diff = "*" if self.__disk_diff else ""
        self.status_right.text = self.cursor_full(f"{diff} :: ")

    def _on_scroll(self, *a):
        start, finish = self.code_entry.visible_line_range()
        finish = min(finish, len(self.code_entry._lines))
        self.line_gutter.text = "\n".join(
            f"{i+1:>4}" for i in range(start, finish)
        )

    def _on_focus(self, w, focus):
        self.im.active = focus

    def _on_text(self, *a):
        error_summary = self.session.get_error_summary(self.code_entry.text)
        self.status_left.text = error_summary
        self._on_cursor()
        kx.schedule_once(self._on_scroll, 0)
