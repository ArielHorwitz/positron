"""Project search."""

from itertools import islice
from .. import kex as kx, FONTS_DIR
from ...util import settings


FONT = str(FONTS_DIR / settings.get("editor.font"))
UI_FONT_SIZE = settings.get("ui.font_size")
MAX_RESULTS = settings.get("project.max_search_results")


class Search(kx.Modal):
    results = kx.ListProperty([])

    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.set_size(hx=0.8, hy=0.8)
        self.make_bg(kx.get_color("cyan", v=0.2))
        self.title = kx.Label(text="Search Project")
        self.title.set_size(y=40)

        # Search
        self.search_entry = kx.Entry(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
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
        self.bind(parent=self._on_parent, results=self._on_results)
        self.search_entry.bind(focus=self._on_search_focus)
        self._on_search_text(self.search_entry, "")
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
        if not self.results:
            return
        editor = self.container.code_editor
        result = self.results[0]
        editor.load(result.module_path)
        editor.set_cursor(result.line, result.column)
        self.dismiss()

    def _scroll_down(self, count=1):
        for i in range(count):
            self.results.append(self.results.pop(0))

    def _scroll_up(self, count=1):
        for i in range(count):
            self.results.insert(0, self.results.pop())

    def _on_results(self, w, results):
        labels = []
        append = labels.append
        for r in results:
            append(
                f"{r.line:>5},{r.column:>3} :: {r.module_name} :: {r.description}"[:70]
            )
        self.results_label.text = "\n".join(labels)

    def _on_search_text(self, w, text):
        results = self.session.search_project(text)
        self.results = list(islice(results, MAX_RESULTS))

    def _on_search_focus(self, w, focus):
        if not focus:
            kx.schedule_once(self.dismiss, 0)

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is None:
            return
        self.search_entry.set_focus()
        self.search_entry.select_all()
        self._on_search_text(self.search_entry, self.search_entry.text)
