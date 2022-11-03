"""Code editor widget."""

from typing import Optional
import re
import os.path
import arrow
from pathlib import Path
from pygments.util import ClassNotFound as LexerClassNotFound
from pygments.styles import get_style_by_name, STYLE_MAP
from pygments.lexers import get_lexer_for_filename
from pygments.lexers.markup import MarkdownLexer
from jedi.api.classes import Completion
from .. import kex as kx, FONTS_DIR
from ...util import settings
from ...util.file import file_load, file_dump, try_relative
from ...util.snippets import find_snippets, Snippet


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
CURSOR_PAUSE_TIMEOUT = settings.get("editor.cursor_pause_timeout")
CURSOR_SCROLL_OFFSET = settings.get("editor.cursor_scroll_offset")
GUTTER_WIDTH = settings.get("editor.gutter_width")
BACKGROUND_RGB = settings.get("editor.bg_color")
assert len(BACKGROUND_RGB) == 3
BACKGROUND_COLOR = kx.XColor(*BACKGROUND_RGB, v=settings.get("editor.bg_brightness"))
DEFOCUS_BRIGHTNESS = settings.get("editor.defocus_brightness")
MAX_COMPLETIONS = 10
COMPLETION_DISABLE_AFTER = set(" \t\n\r!#$%&()*+,-/:;<=>?@[\]^{|}~")


def timestamp():
    return arrow.now().format("HH:mm:ss")


class CodeEditor(kx.Anchor):
    _cached_code_completions = kx.ListProperty([])

    def __init__(self, session, uid: int, file: Path):
        super().__init__()
        self.session = session
        self.__uid = uid
        assert isinstance(file, Path)
        self._current_file = file.expanduser().resolve()
        self.__disk_modified_time = None
        self.__disk_diff = False
        self.__disk_cache = None
        self.__find_text = ""
        self.__cached_selected_text = ""
        self.im = kx.InputManager(name=f"Code editor {uid}")
        # Code
        self.code_entry = kx.CodeEntry(
            font_name=FONT,
            font_size=FONT_SIZE,
            auto_indent=True,
            do_wrap=False,
            style_name=STYLE_NAME,
            background_color=BACKGROUND_COLOR.rgba,
            scroll_distance=750,
            cursor_pause_timeout=CURSOR_PAUSE_TIMEOUT,
            cursor_scroll_offset=CURSOR_SCROLL_OFFSET,
            _focus_brightness_diff=DEFOCUS_BRIGHTNESS,
        )
        self.code_entry.focus = True
        self.code_entry.bind(
            scroll_y=self._on_scroll,
            size=self._on_size,
            focus=self._on_focus,
            cursor=self._on_cursor,
            text=self._on_text,
            selection_text=self._on_selection_text,
        )
        # Gutter
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
        line_gutter_frame.set_size(x=GUTTER_WIDTH)
        line_gutter_frame.add(line_gutter_top_padding, self.line_gutter)
        code_frame = kx.Box()
        code_frame.add(line_gutter_frame, self.code_entry)
        # Status bar
        self.status_left = kx.Label(font_name=FONT, font_size=14, halign="left")
        self.status_right = kx.Label(font_name=FONT, font_size=14, halign="right")
        status_bar = kx.Anchor()
        status_bar.set_size(hx=0.95)
        status_bar.add(self.status_left, self.status_right)
        status_bar_frame = kx.Anchor()
        status_bar_frame.set_size(y=25)
        status_bar_frame.add(status_bar)
        # Assemble
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(status_bar_frame, code_frame)
        self.add(main_frame)
        # Completion popup
        self.completion_label = kx.Label(
            halign="left",
            font_name=FONT,
            font_size=FONT_SIZE,
            fixed_width=True,
        )
        self.completion_label.make_bg(kx.get_color("blue", v=0.2, a=0.4))
        self.completion_label.set_size(x=300, y=30)
        completion_layout = kx.Relative()
        completion_layout.add(self.completion_label)
        self.completion_modal = kx.Modal(container=self, name="Completion popup")
        self.completion_modal.add(completion_layout)
        self.code_entry.bind(
            on_cursor_pause=self._on_cursor_pause,
            cursor_pos=self._on_cursor_pos,
        )
        self.bind(_cached_code_completions=self._on_cached_code_completions)
        # Controls
        self.set_focus = self.code_entry.set_focus
        for reg_args in [
            ("Open settings", self._open_settings, "f8"),
            ("Reload", self.reload, "^ l"),
            ("Save", self.save, "^ s"),
            ("Delete file", self.delete_file, "^+ delete"),
            ("Duplicate lines", self.code_entry.duplicate, "^+ d", True),
            ("Shift lines up", lambda: self.code_entry.shift_lines(-1), "!+ up", True),
            ("Shift lines down", lambda: self.code_entry.shift_lines(1), "!+ down", True),
            ("Find next", self.find_next, "^ ]", True),
            ("Find previous", self.find_prev, "^ [", True),
            ("Complete code", self._do_complete, "! enter"),
            ("Scroll up code comps", self._scroll_up_completions, "! up", True),
            ("Scroll down code comps", self._scroll_down_completions, "! down", True),
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
            self.code_entry.reset_cursor_selection()
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
        self._refresh_status_diff()

    def _update_lexer(self):
        try:
            lexer = get_lexer_for_filename(self._current_file.name)
        except LexerClassNotFound:
            lexer = MarkdownLexer()
        self.code_entry.lexer = lexer

    def _open_settings(self):
        self.load(file=settings.SETTINGS_FILE)

    # Cursor management
    @property
    def cursor(self):
        column, line = self.code_entry.cursor
        line += 1
        return line, column

    def set_cursor(self, line: int, column: int):
        code = self.code_entry
        code.cursor = column, line - 1
        code.scroll_to_cursor()
        code.cancel_cursor_pause()

    def cursor_full(self, sep: str = "::"):
        line, column = self.cursor
        path = try_relative(self._current_file, self.session.project_path)
        return f"{path}{sep}{line},{column}"

    # Code inspection
    @property
    def selected_text(self):
        return self.__cached_selected_text

    def find_next(self, text: Optional[str] = None):
        if text is not None:
            self.__find_text = text
        self.code_entry.focus = True
        self.code_entry.find_next(self.__find_text)

    def find_prev(self, text: Optional[str] = None):
        self.code_entry.focus = True
        if text is not None:
            self.__find_text = text
        self.code_entry.find_prev(self.__find_text)

    def goto_line(self, line_number: int, end: bool = False):
        assert isinstance(line_number, int)
        assert line_number > 0
        self.code_entry.cursor = end * 10**6, line_number - 1

    def _do_complete(self):
        code = self.code_entry
        if not self.completion_modal.parent:
            self._find_code_completions()
        comps = self._cached_code_completions
        if not comps:
            return
        comp = comps[0]
        if isinstance(comp, Snippet):
            for i in range(len(self._get_last_word())):
                code.do_backspace()
            self.insert_snippet(comp)
        elif isinstance(comp, Completion):
            for i in range(comp.get_completion_prefix_length()):
                code.do_backspace()
            code.insert_text(comp.name)
        else:
            raise ValueError(f"Unknown completion type: {comp!r}")

    def insert_snippet(self, snippet):
        code = self.code_entry
        original_cidx = code.cursor_index()
        code.insert_text(snippet.text)
        move = snippet.move
        if move  < 0:  # move to beginning
            move = code.cursor_index() - original_cidx
        final_cidx = code.cursor_index() - move
        code.cursor = code.get_cursor_from_index(final_cidx)
        select = snippet.select
        if select < 0:  # select all
            select = final_cidx - original_cidx
        if select:
            start, end = final_cidx - select, final_cidx
            kx.schedule_once(lambda *a: code.select_text(start, end), 0)

    def _get_last_word(self, text=None):
        if text is None:
            text = self.code_entry.text[:self.code_entry.cursor_index()]
        if not text:
            return ""
        full_len = len(text)
        idx = min(10, full_len)
        whitespaces = list(re.finditer(r'[\s]+', text[full_len - idx:]))
        while True:
            partial_text = text[full_len - idx:]
            whitespaces = list(re.finditer(r'[\s]+', partial_text))
            if whitespaces:
                last_ws = whitespaces[-1].end()
                return partial_text[last_ws:]
            idx *= 2
            if idx > full_len:
                return text

    # Events
    def _on_cursor(self, *a):
        self._refresh_status_diff()
        self.completion_modal.dismiss()

    def _on_cursor_pause(self, *args):
        self._find_code_completions()
        self.completion_modal.open()

    def _find_code_completions(self, *args):
        self._cached_code_completions = []
        code = self.code_entry
        if code.selection_text:
            return
        code_text = code.text
        line, col = self.cursor
        cidx = code.cursor_index()
        last_word = self._get_last_word(code_text[:cidx])
        # Code completion
        last_char = code_text[cidx-1:cidx]
        if not last_char:
            return
        if last_char in COMPLETION_DISABLE_AFTER:
            return
        comps = self.session.get_completions(
            self.file,
            code_text,
            line,
            col,
            MAX_COMPLETIONS,
            fuzzy=True,
        )
        comps = [
            c for c in comps
            if c.name != last_word[-len(c.name):]
        ]
        # Snippets
        snips = []
        if last_word:
            snips = list(find_snippets(last_word))
        self._cached_code_completions = snips + comps

    def _on_cached_code_completions(self, w, comps):
        text_lines = []
        for c in reversed(comps):
            if isinstance(c, Snippet):
                text_lines.append(f"¬ {c.name}")
            elif isinstance(c, Completion):
                text_lines.append(c.name)
            else:
                raise ValueError(f"Unknown completion type: {c!r}")
        self.completion_label.text = "\n".join(text_lines)

    def _scroll_down_completions(self, *args):
        if self._cached_code_completions:
            p = self._cached_code_completions.pop(0)
            self._cached_code_completions.append(p)

    def _scroll_up_completions(self, *args):
        if self._cached_code_completions:
            p = self._cached_code_completions.pop()
            self._cached_code_completions.insert(0, p)

    def _on_cursor_pos(self, w, cpos):
        fixed_cpos = self.to_widget(*cpos, relative=True)
        self.completion_label.pos = self.to_widget(*fixed_cpos)

    def _on_scroll(self, w, scroll):
        self._refresh_line_gutters()

    def _refresh_line_gutters(self, *a):
        start, finish = self.code_entry.visible_line_range()
        finish = min(finish, len(self.code_entry._lines))
        self.line_gutter.text = "\n".join(
            f"{i+1:>4}" for i in range(start, finish)
        )

    def _on_size(self, w, size):
        self._refresh_line_gutters()
        self.code_entry.scroll_to_cursor()
        self.code_entry.cancel_cursor_pause()

    def _on_focus(self, w, focus):
        self.im.active = focus

    def _on_text(self, *a):
        error_summary = self.session.get_error_summary(self.code_entry.text)
        self.status_left.text = error_summary
        self._on_cursor()
        kx.schedule_once(self._refresh_line_gutters)

    def _on_selection_text(self, w, text):
        if self.code_entry.focus:
            self.__cached_selected_text = text

    def _refresh_status_diff(self, *a):
        diff = "*" if self.__disk_diff else ""
        self.status_right.text = self.cursor_full(f"{diff} :: ")
