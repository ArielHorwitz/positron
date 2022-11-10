"""Project search."""

from itertools import islice
from .. import kex as kx, FONTS_DIR
from ...util import settings


FONT = str(FONTS_DIR / settings.get("ui.font"))
UI_FONT_SIZE = settings.get("ui.font_size")
MAX_RESULTS = settings.get("project.max_search_results")
# TODO find more reliable method - CHAR_WIDTH may only work with the builtin font
CHAR_SIZE = kx.CoreLabel(font=FONT, font_size=UI_FONT_SIZE).get_extents(text="A")
CHAR_WIDTH, LINE_HEIGHT = CHAR_SIZE
CHAR_WIDTH -= 1
DESCRIPTION_COLOR = "#44dd44"
LOCATION_COLOR = "#bb44bb"


class Search(kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self._results = []
        self.set_size(hx=0.8, hy=0.8)
        self.make_bg(kx.get_color("cyan", v=0.2))
        self.title = kx.Label(text="Search Project")
        self.title.set_size(y=40)

        # Search
        self.search_entry = kx.Entry(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            halign="center",
            write_tab=False,
            background_color=kx.XColor(0.2, 0.6, 1, v=0.2).rgba,
            multiline=False,
        )
        self.search_entry.set_size(y=40)
        self.search_entry.bind(text=self._on_search_text)

        # Tree
        self.results_label = kx.Label(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            halign="left",
            valign="top",
        )

        # Assemble
        panel_frame = kx.Box(orientation="vertical")
        panel_frame.add(self.search_entry, self.results_label)
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(self.title, panel_frame)
        self.add(main_frame)

        # Events
        self.bind(parent=self._on_parent)
        self.search_entry.bind(focus=self._on_search_focus)
        self._on_search_text()
        self.im.register("Load", self._do_load, "enter")
        self.im.register("Load (2)", self._do_load, "numpadenter")
        self.im.register("Scroll down", self._scroll_down, "down", allow_repeat=True)
        self.im.register("Scroll up", self._scroll_up, "up", allow_repeat=True)
        self.im.register(
            "Page down", lambda: self._scroll_down(10), "pagedown", allow_repeat=True,
        )
        self.im.register(
            "Page up", lambda: self._scroll_up(10), "pageup", allow_repeat=True,
        )

    def _do_load(self):
        if not self._results:
            return
        editor = self.container.code_editor
        result = self._results[0]
        editor.load(result.module_path)
        editor.set_cursor(result.line, result.column)
        self.dismiss()

    def _scroll_down(self, count=1):
        for i in range(count):
            self._results.append(self._results.pop(0))
        self._refresh_results()

    def _scroll_up(self, count=1):
        for i in range(count):
            self._results.insert(0, self._results.pop())
        self._refresh_results()

    def _refresh_results(self, *args):
        lines = []
        append = lines.append
        line_width = max(1, int(self.results_label.width / CHAR_WIDTH))
        module_width = line_width - 12
        for r in self._results:
            mod_name = f" {r.module_name}"
            append(_wrap_color(
                f"{mod_name:¯>{module_width}} ::{r.line:>5},{r.column:>3}",
                LOCATION_COLOR,
            ))
            desc = f"{r.description[:line_width]:<{line_width}}"
            append(_wrap_color(desc, DESCRIPTION_COLOR))
        self.results_label.text = "\n".join(lines)

    def _on_search_text(self, *args):
        results = self.session.search_project(self.search_entry.text)
        self._results = list(islice(results, MAX_RESULTS))
        self._refresh_results()

    def _on_search_focus(self, w, focus):
        if not focus:
            kx.schedule_once(self.dismiss, 0)

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is None:
            return
        self.search_entry.set_focus()
        self.search_entry.select_all()
        self._on_search_text()


def _wrap_color(t, color):
    return f"[color={color}]{t}[/color]"
