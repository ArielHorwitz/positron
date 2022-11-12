"""Code editor widget."""

from loguru import logger
from typing import Optional
import re
import os.path
import arrow
import functools
from pathlib import Path
from pygments.util import ClassNotFound as LexerClassNotFound
from pygments.styles import STYLE_MAP
from pygments.lexers import get_lexer_for_filename
from pygments.lexers.markup import MarkdownLexer
from jedi.api.classes import Completion
from .. import kex as kx, FONTS_DIR
from ...util import settings
from ...util.file import file_load, file_dump
from ...util.snippets import find_snippets, Snippet


STYLE_NAME = settings.get("editor.style")
logger.info(f"Available styles: {list(STYLE_MAP.keys())}")
if STYLE_NAME not in STYLE_MAP:
    STYLE_NAME = "default"
logger.info(f"Chosen style: {STYLE_NAME}")
FONT = str(FONTS_DIR / settings.get("editor.font"))
FONT_SIZE = settings.get("editor.font_size")
AUTO_LOAD = settings.get("editor.auto_load")
GUTTER_PADDING = settings.get("editor.gutter_padding")
DISK_DIFF_INTERVAL = settings.get("editor.disk_diff_interval")
CURSOR_PAUSE_TIMEOUT = settings.get("editor.cursor_pause_timeout")
CURSOR_SCROLL_OFFSET = settings.get("editor.cursor_scroll_offset")
GUTTER_WIDTH = settings.get("editor.gutter_width")
BACKGROUND_COLOR = kx.XColor(*settings.get("editor.bg_color"))
DEFOCUS_BRIGHTNESS = settings.get("editor.defocus_brightness")
ERROR_CHECK_COOLDOWN = settings.get("editor.error_check_cooldown")
MAX_COMPLETIONS = 10
COMPLETION_DISABLE_AFTER = set(" \t\n\r!#$%&()*+,-/:;<=>?@[\]^{|}~")  # noqa: W605
STATUS_BG = kx.XColor(*settings.get("ui.status.normal"))
STATUS_BG_WARN = kx.XColor(*settings.get("ui.status.warn"))
STATUS_BG_ERROR = kx.XColor(*settings.get("ui.status.error"))
MAX_LINE_LENGTH = settings.get("linter.max_line_length")
LINE_LENGTH_HINT_COLOR = settings.get("editor.line_width_color")
CHAR_SIZE = kx.CoreLabel(font=FONT, font_size=FONT_SIZE).get_extents(text="a")
CHAR_WIDTH, LINE_HEIGHT = CHAR_SIZE
MAX_LINE_WIDTH = CHAR_WIDTH * (MAX_LINE_LENGTH + 1)


def _timestamp():
    return arrow.now().format("HH:mm:ss")


@functools.cache
def _format_humanized(m):
    if m is None:
        return ""
    m = m.removesuffix(' ago')
    if m == "a minute":
        m = "1m"
    m = m.replace(" seconds", "s").replace(" minutes", "m").replace(" hours", "h")
    m = m.replace(" days", "D").replace(" months", "M").replace(" years", "Y")
    return f"[{m}] "


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
        self.__errors = None
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
        # Cursor status bar
        status_kw = {"font_name": FONT, "font_size": FONT_SIZE}
        self.status_cursor_context = kx.Label(halign="left", **status_kw)
        self.status_cursor_context.set_size(hx=0.95)
        self.status_file_cursor = kx.Label(halign="right", **status_kw)
        self.status_file_cursor.set_size(hx=0.95)
        self.status_bar_cursor = kx.Anchor()
        self.status_bar_cursor.set_size(y=LINE_HEIGHT)
        self.status_bar_cursor.add(self.status_cursor_context, self.status_file_cursor)
        # Errors status bar
        self.status_errors = kx.Label(halign="center", **status_kw)
        self.status_errors.set_size(hx=0.95)
        self.status_bar_errors = kx.Anchor()
        self.status_bar_errors.set_size(y=LINE_HEIGHT)
        self.status_bar_errors.add(self.status_errors)
        self.__update_errors_trigger = kx.create_trigger(
            self._update_errors,
            ERROR_CHECK_COOLDOWN,
        )
        # Assemble
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(self.status_bar_cursor, code_frame, self.status_bar_errors)
        self.add(main_frame)
        # Line length hint
        with self.canvas.after:
            kx.Color(*LINE_LENGTH_HINT_COLOR)
            self.line_width_hint = kx.Rectangle(size=(2, 10_000))
            kx.Color()
        self._reposition_line_width_hint()
        self.code_entry.bind(
            pos=self._reposition_line_width_hint,
            size=self._reposition_line_width_hint,
        )
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
            ("Open settings", self._open_settings, "f11"),
            ("Reload", self.reload, "^ l"),
            ("Save", self.save, "^ s"),
            ("Delete file", self.delete_file, "^+ delete"),
            ("Duplicate lines", self.code_entry.duplicate, "^+ d", True),
            ("Shift lines up", lambda: self.code_entry.shift_lines(-1), "!+ up", True),
            (
                "Shift lines down",
                lambda: self.code_entry.shift_lines(1),
                "!+ down",
                True,
            ),
            ("Find next", self.find_next, "^ ]", True),
            ("Find previous", self.find_prev, "^ [", True),
            ("Complete code", self._do_complete, "! enter"),
            ("Scroll up code comps", self._scroll_up_completions, "! up", True),
            ("Scroll down code comps", self._scroll_down_completions, "! down", True),
            ("Next error", self.scroll_to_error, "^ e", True),
            ("Comment", self.make_comment, "^ \\"),
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
        logger.info(f"Saved  @ {_timestamp()} to: {file}")
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
            logger.info(f"Loaded @ {_timestamp()} from: {file}")
        else:
            text = ""
            logger.info(f"New unsaved file: {file}")
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
            logger.info(f"Deleted @ {_timestamp()} file: {self._current_file}")
            self.load()

    def _get_disk_content(self, file: Path) -> str:
        if not file.exists():
            return None
        return file_load(file)

    def _get_disk_mod_date(self, file: Path):
        return arrow.get(os.path.getmtime(file)) if file.exists() else None

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
                logger.info(f"Cached @ {_timestamp()} for: {self._current_file}")
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
        if move < 0:  # move to beginning
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

    def scroll_to_error(self):
        next_error = self._get_next_error(include_cursor_index=False)
        if next_error:
            self.set_cursor(next_error.line, next_error.column)

    def make_comment(self):
        self.code_entry.toggle_prepend("# ")

    # Events
    def _on_cursor(self, *a):
        self._refresh_status_diff()
        self.completion_modal.dismiss()
        kx.schedule_once(self._refresh_context)

    def _on_cursor_pause(self, *args):
        self._refresh_status_errors()
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

    def _reposition_line_width_hint(self, *args):
        code = self.code_entry
        self.line_width_hint.pos = code.x + MAX_LINE_WIDTH, code.y
        self.line_width_hint.size = 2, code.height

    def _on_focus(self, w, focus):
        self.im.active = focus

    def _on_text(self, *a):
        ev = self.__update_errors_trigger
        if ev.is_triggered:
            ev.cancel()
        ev()
        self._on_cursor()
        kx.schedule_once(self._refresh_line_gutters)

    def _on_selection_text(self, w, text):
        if self.code_entry.focus:
            self.__cached_selected_text = text

    def _refresh_status_diff(self, *a):
        self.status_file_cursor.text = self._cursor_full()
        bg = STATUS_BG_WARN if self.__disk_diff else STATUS_BG
        self.status_bar_cursor.make_bg(bg)

    def _cursor_full(self):
        line, column = self.cursor
        path = self._current_file
        ppath = self.session.project_path
        if path.is_relative_to(ppath):
            path = f"$/{path.relative_to(ppath)}"
        elif path.is_relative_to(Path.home()):
            path = f"~/{path.relative_to(Path.home())}"
        modified = ""
        if self.__disk_modified_time:
            modified = _format_humanized(self.__disk_modified_time.humanize())
        diff = "*" if self.__disk_diff else ""
        return f"{modified}{path}{diff} ::{line:>4},{column:<3}"

    def _refresh_context(self, *a):
        code = self.code_entry
        line, col = self.cursor
        context = self.session.get_context(self.file, code.text, line, col)
        if context is None:
            context = "__ unknown context __"
        elif context.full_name is None:
            context = f"__unknown_context__.{context.name}"
        else:
            context = context.full_name[len(context.module_name) + 1:] or "__module__"
        self.status_cursor_context.text = context

    def _update_errors(self, *args):
        errors = []
        if self._current_file.suffix == ".py":
            errors = self.session.get_errors(self.code_entry.text)
        self.__errors = errors
        self._refresh_status_errors()

    def _refresh_status_errors(self, *args):
        error = self._get_next_error(include_cursor_index=True)
        if not error:
            self.status_errors.text = "No errors :)"
            self.status_bar_errors.make_bg(STATUS_BG)
            return
        summary = f"Error @ {error.line},{error.column} :: {error.message}"
        count = len(self.__errors)
        if count > 1:
            summary = f"{summary}  ( + {count - 1} more errors)"
        self.status_errors.text = summary
        self.status_bar_errors.make_bg(STATUS_BG_ERROR)

    def _get_next_error(self, include_cursor_index: bool = True):
        if not self.__errors:
            return None
        cidx = self.code_entry.cursor_index()
        for e in self.__errors:
            eidx = self.code_entry.cursor_index((e.column, e.line-1))
            if (
                (include_cursor_index and eidx >= cidx)
                or (not include_cursor_index and eidx > cidx)
            ):
                return e
        return self.__errors[0]
