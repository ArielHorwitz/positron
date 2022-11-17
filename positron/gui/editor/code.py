"""Code editor widget."""

from loguru import logger
from typing import Optional
import traceback
import re
import os.path
import arrow
from pathlib import Path
from pygments.util import ClassNotFound as LexerClassNotFound
from pygments.styles import STYLE_MAP
from pygments.lexers import get_lexer_for_filename
from pygments.lexers.markup import MarkdownLexer
from jedi.api.classes import Completion
from .. import kex as kx, FONT_KW, UI_FONT_KW, CHAR_WIDTH, LINE_HEIGHT
from ...util import settings
from ...util.file import file_load, file_dump
from ...util.snippets import find_snippets, Snippet


logger.info(f"Available styles: {list(STYLE_MAP.keys())}")
MAX_COMPLETIONS = 10
COMPLETION_DISABLE_AFTER = set(" \t\n\r!#$%&()*+,-/:;<=>?@[\]^{|}~")  # noqa: W605
STATUS_FONT_KW = dict(
    font_name=UI_FONT_KW["font_name"],
    font_size=FONT_KW["font_size"],
    italic=True,
    shorten=True,
)


def _timestamp():
    return arrow.now().format("HH:mm:ss")


def _format_humanized(a: arrow.Arrow, /) -> str:
    now = arrow.now()
    assert a < now
    h = a.humanize().removesuffix(' ago')
    if h == "just now":
        diff = now - a
        seconds = round(diff.total_seconds())
        return f"{seconds} seconds"
    if h.startswith("a "):
        h = f"1 {h[2:]}s"
    return h


class CodeEditor(kx.Anchor):
    _cached_code_completions = kx.ListProperty([])

    def __init__(self, session, uid: int, file: Path):
        super().__init__()
        self.session = session
        self.__uid = uid
        assert isinstance(file, Path)
        self._current_file = file.expanduser().resolve()
        self.__gutter_width = 3  # Any int, should be updated with settings refresh
        self.__max_line_width = 1  # Any int, should be updated with settings refresh
        self.__disk_modified_time: Optional[arrow.Arrow] = None
        self.__disk_diff = False
        self.__disk_cache = None
        self.__find_text = ""
        self.__errors = []
        self.__last_errors_hash = None
        self.__cached_selected_text = ""
        self.__status_bg = kx.XColor(*settings.get("ui.status.normal"))
        self.__status_bg_warn = kx.XColor(*settings.get("ui.status.warn"))
        self.__status_bg_error = kx.XColor(*settings.get("ui.status.error"))
        self.im = kx.InputManager(name=f"Code editor {uid}")
        # Code
        self.code_entry = kx.CodeEntry(
            auto_indent=True,
            do_wrap=False,
            style_name=settings.get("editor.style"),
            scroll_distance=750,
            **FONT_KW,
        )
        self.code_entry.focus = True
        self.code_entry.bind(
            scroll_y=self._refresh_line_gutters,
            size=self._on_size,
            focus=self._on_focus,
            cursor=self._on_cursor,
            text=self._on_text,
            selection_text=self._on_selection_text,
        )
        # Gutter
        self.line_gutter = kx.Label(
            valign="top",
            halign="right",
            padding_y=self.code_entry.padding[1],
            **FONT_KW,
        )
        # Cursor status bar
        self.status_cursor_context = kx.Label(halign="left", **STATUS_FONT_KW)
        self.status_cursor_context.set_size(hx=0.95)
        self.status_file_cursor = kx.Label(halign="right", **STATUS_FONT_KW)
        self.status_file_cursor.set_size(hx=0.95)
        self.status_bar_cursor = kx.Box(orientation="vertical")
        self.status_bar_cursor.set_size(y=LINE_HEIGHT * 2)
        self.status_bar_cursor.add(self.status_file_cursor, self.status_cursor_context)
        # Errors status bar
        self.status_errors = kx.Label(
            halign="left",
            shorten_from="right",
            **STATUS_FONT_KW,
        )
        self.status_errors.set_size(hx=0.95)
        self.status_bar_errors = kx.Anchor()
        self.status_bar_errors.set_size(y=LINE_HEIGHT)
        self.status_bar_errors.add(self.status_errors)
        self.__update_errors_trigger = kx.snoozing_trigger(
            self.update_errors,
            settings.get("editor.error_check_cooldown"),
        )
        # Assemble
        code_frame = kx.Box()
        code_frame.add(self.line_gutter, self.code_entry)
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(self.status_bar_cursor, code_frame, self.status_bar_errors)
        self.add(main_frame)
        # Line length hint
        with self.canvas.after:
            self.line_width_hint_color = kx.Color()
            self.line_width_hint = kx.Rectangle(size=(2, 10_000))
            kx.Color()
        self._reposition_line_width_hint()
        self.code_entry.bind(
            pos=self._reposition_line_width_hint,
            size=self._reposition_line_width_hint,
            scroll_x=self._reposition_line_width_hint,
        )
        # Completion popup
        self.completion_label = kx.Label(halign="left", fixed_width=True, **FONT_KW)
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
            ("Toggle case", self.code_entry.toggle_case, "^ u"),
            ("Join/split lines", self.code_entry.join_split_lines, "^+ j"),
        ]:
            self.im.register(*reg_args)
        # Bind to settings
        self._do_trigger_refresh_settings = kx.create_trigger(self._refresh_settings)
        for setting_name in self._refresh_settings_bound_names:
            settings.bind(setting_name, self._trigger_refresh_settings)
        self._trigger_refresh_settings()
        if settings.get("editor.auto_load"):
            self.load()
        self.__disk_diff_ev = kx.schedule_interval(
            self._check_disk_diff,
            settings.get("editor.disk_diff_interval"),
        )

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

    def load(
        self,
        file: Optional[Path] = None,
        /,
        *,
        reset_cursor: bool = True,
        cursor: Optional[tuple[int, int]] = None,
    ):
        if file is None:
            file = self._current_file
        if file.exists():
            fsize_kb = file.stat().st_size / 2**10
            if fsize_kb > settings.get("editor.max_file_size_kb"):
                logger.warning(
                    f"Cannot open {file} due to large size: {fsize_kb:.2f} KB"
                )
                return
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
        old_cursor = self.code_entry.cursor
        self.code_entry.text = text
        if reset_cursor or cursor is not None:
            if cursor:
                self.set_cursor(*cursor)
            else:
                self.code_entry.reset_cursor_selection()
        else:
            self.code_entry.cursor = old_cursor
        self.code_entry.cancel_cursor_pause()
        self.update_errors()

    def reload(self, *args):
        self.load(reset_cursor=False)

    def delete_file(self):
        if self._current_file.is_file():
            self._current_file.unlink()
            logger.info(f"Deleted @ {_timestamp()} file: {self._current_file}")
            self.load()

    def _get_disk_content(self, file: Path) -> str:
        try:
            return file_load(file)
        except UnicodeDecodeError as e:
            lmsg = "\n".join(traceback.format_exception(e))
            logger.warning(f"Failed to load file {file}, see traceback:\n{lmsg}")
        except FileNotFoundError:
            pass
        return None

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
                # logger.info(f"Cached @ {_timestamp()} for: {self._current_file}")
            self.__disk_diff = self.__disk_cache != self.code_entry.text
        self._refresh_status_diff()

    def _update_lexer(self):
        try:
            lexer = get_lexer_for_filename(self._current_file.name)
        except LexerClassNotFound:
            lexer = MarkdownLexer()
        self.code_entry.lexer = lexer

    def _open_settings(self):
        self.load(settings.SETTINGS_FILE)

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
        self.update_errors()
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

    def _refresh_line_gutters(self, *a):
        start, finish = self.code_entry.visible_line_range()
        finish = min(finish, len(self.code_entry._lines))
        self.line_gutter.text = "\n".join(
            f"{str(i+1)[:self.__gutter_width]:>{self.__gutter_width}}"
            for i in range(start, finish)
        )

    def _on_size(self, w, size):
        self._refresh_line_gutters()
        self.code_entry.scroll_to_cursor()
        self.code_entry.cancel_cursor_pause()

    def _reposition_line_width_hint(self, *args):
        code = self.code_entry
        x = code.x + self.__max_line_width - code.scroll_x
        self.line_width_hint.pos = x, code.y
        self.line_width_hint.size = 2, code.height

    def _on_focus(self, w, focus):
        self.im.active = focus

    def _on_text(self, *a):
        self.__update_errors_trigger()
        self._on_cursor()
        kx.schedule_once(self._refresh_line_gutters)

    def _on_selection_text(self, w, text):
        if self.code_entry.focus:
            self.__cached_selected_text = text

    def _refresh_status_diff(self, *a):
        self.status_file_cursor.text = self._cursor_full()
        bg = self.__status_bg_warn if self.__disk_diff else self.__status_bg
        self.status_bar_cursor.make_bg(bg)

    def _cursor_full(self):
        line, column = self.cursor
        path = self.session.repr_full_path(self._current_file, include_icon=False)
        icon = self.session.get_path_icon(self._current_file)
        modified = ""
        if self.__disk_modified_time:
            modified = _format_humanized(self.__disk_modified_time)
        diff = "*" if self.__disk_diff else ""
        return f"[{modified}{diff}] {icon} :: {path} ::{line:>4},{column:<3}"

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

    def update_errors(self, *args):
        if self._current_file.suffix == ".py":
            code = self.code_entry.text
            code_hash = hash(code)
            if self.__last_errors_hash != code_hash:
                logger.debug(f"Getting errors for {code_hash=}")
                self.__last_errors_hash = code_hash
                errors = self.session.get_errors(code)
            else:
                errors = self.__errors
        else:
            errors = []
        self.__errors = errors
        self._refresh_status_errors()
        return errors

    def _refresh_status_errors(self, *args):
        error = self._get_next_error(include_cursor_index=True)
        if not error:
            self.status_errors.text = "No errors :)"
            self.status_bar_errors.make_bg(self.__status_bg)
            return
        count = len(self.__errors)
        self.status_errors.text = (
            f"[b]{str(count):>3} errors[/b], next @ "
            f"{error.line},{error.column} :: {error.message}"
        )
        self.status_bar_errors.make_bg(self.__status_bg_error)

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

    def _trigger_refresh_settings(self, *args):
        self._do_trigger_refresh_settings()

    def _refresh_settings(self, *args):
        logger.debug("Code editor refreshing settings")
        entry = self.code_entry
        entry.style_name = settings.get("editor.style")
        entry.cursor_pause_timeout = settings.get("editor.cursor_pause_timeout")
        entry.cursor_scroll_offset = settings.get("editor.cursor_scroll_offset")
        entry.defocus_brightness = settings.get("editor.defocus_brightness")
        entry.set_background(kx.XColor(*settings.get("editor.bg_color")).rgba)
        self.__gutter_width = settings.get("editor.gutter_width")
        line_gutter = self.line_gutter
        line_gutter.set_size(x=self.__gutter_width * CHAR_WIDTH)
        line_gutter.make_bg(kx.XColor(*settings.get("editor.gutter_bg_color")))
        line_gutter.color = settings.get("editor.gutter_text_color")
        self._refresh_line_gutters()
        errors_trigger = self.__update_errors_trigger.ev
        errors_trigger.timeout = settings.get("editor.error_check_cooldown")
        self.__disk_diff_ev.timeout = settings.get("editor.disk_diff_interval")
        self.__status_bg = kx.XColor(*settings.get("ui.status.normal"))
        self.__status_bg_warn = kx.XColor(*settings.get("ui.status.warn"))
        self.__status_bg_error = kx.XColor(*settings.get("ui.status.error"))
        self.__max_line_width = (
            CHAR_WIDTH * (settings.get("linter.max_line_length") + 1)
        )
        lhint_color = settings.get("editor.line_width_hint_color")
        self.line_width_hint_color.rgba = kx.XColor(*lhint_color).rgba

    _refresh_settings_bound_names = (
        "editor.style",
        "editor.bg_color",
        "editor.cursor_pause_timeout",
        "editor.cursor_scroll_offset",
        "editor.defocus_brightness",
        "editor.gutter_width",
        "editor.gutter_bg_color",
        "editor.gutter_text_color",
        "editor.error_check_cooldown",
        "editor.disk_diff_interval",
        "editor.line_width_hint_color",
        "linter.max_line_length",
    )
