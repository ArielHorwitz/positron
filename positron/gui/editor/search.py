"""Project search."""

from loguru import logger
from .. import kex as kx, FONTS_DIR
from ...util import settings
from ...util.file import file_load, search_text


FONT = str(FONTS_DIR / settings.get("ui.font"))
UI_FONT_SIZE = settings.get("ui.font_size")
MAX_RESULTS = settings.get("project.max_search_results")
REFRESH_DELAY = settings.get("project.text_search_cooldown")
# TODO find more reliable method - CHAR_WIDTH may only work with the builtin font
CHAR_SIZE = kx.CoreLabel(font=FONT, font_size=UI_FONT_SIZE).get_extents(text="A")
CHAR_WIDTH, LINE_HEIGHT = CHAR_SIZE
CHAR_WIDTH -= 1
DESCRIPTION_COLOR = "#44dd44"
LOCATION_COLOR = "#bb44bb"
CONTEXT_COLOR = "#22bbbb"


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
            background_color=(0.04, 0.12, 0.2, 1),
            multiline=False,
        )
        self.search_entry.set_size(y=40)
        self.search_entry.bind(text=self._on_search_text)

        # Tree
        self.results_list = kx.List(
            font=FONT,
            font_size=UI_FONT_SIZE,
            on_invoke=self._on_invoke,
            item_height=LINE_HEIGHT * 4,
        )

        # Assemble
        panel_frame = kx.Box(orientation="vertical")
        panel_frame.add(self.search_entry, self.results_list)
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(self.title, panel_frame)
        self.add(main_frame)
        self.search_entry.focus_next = self.results_list
        self.results_list.focus_next = self.search_entry

        # Events
        self._refresh_results = kx.snoozing_trigger(
            self._do_refresh_results,
            REFRESH_DELAY,
        )
        self.bind(parent=self._on_parent)
        self.im.register("Load", self._do_load, "enter")
        self.im.register("Load (2)", self._do_load, "numpadenter")
        self.im.register("Focus ", self._on_down_arrow, "down")

    def _do_load(self, result=None):
        if result is None:
            if not self._results:
                return
            result = self._results[self.results_list.selection]
        location, text = result
        self.container.code_editor.load(location.file, cursor=location.cursor)
        self.dismiss()

    def _on_down_arrow(self):
        if self.search_entry.focus:
            self.results_list.focus = True
        elif self.results_list.focus:
            self.results_list.select(delta=1)

    def _on_invoke(self, w, index, label):
        self._do_load(self._results[index])

    def _do_refresh_results(self, *args):
        pattern = self.search_entry.text
        results = None
        if pattern:
            results = search_text(
                pattern,
                self.session.dir_tree.all_paths,
                max_results=MAX_RESULTS,
            )
        logger.debug(f"{len(results)=}" if results else "No results")
        self._results = results
        self._refresh_list()

    def _refresh_list(self, *args):
        root = self.session.dir_tree.root
        items = []
        append = items.append
        if not self._results:
            self.results_list.items = ["No results."]
            return
        line_width = int(self.results_list.width / CHAR_WIDTH) - 1
        get_context = self.session.get_context
        for location, text in self._results:
            if location.file.suffix == ".py":
                context = get_context(
                    path=location.file,
                    code=file_load(location.file),
                    line=location.cursor[0],
                    col=location.cursor[1],
                ).full_name
            else:
                context = location.file.name
            context = context[-line_width:]
            file = f"$/{location.file.relative_to(root)}"[-line_width:]
            cursor = f"{location.cursor[0]:>4},{location.cursor[1]:>3}"
            loc = f"{file} ::{cursor}"
            text = kx.escape_markup(text).strip()[:line_width]
            item = "\n".join([
                _wrap_color(loc, LOCATION_COLOR),
                _wrap_color(context, CONTEXT_COLOR),
                _wrap_color(text, DESCRIPTION_COLOR),
            ])
            append(item)
        self.results_list.items = items

    def _on_search_text(self, *args):
        self._refresh_results()

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is None:
            return
        self.search_entry.set_focus()
        self.search_entry.select_all()
        self._on_search_text()


def _wrap_color(t, color):
    return f"[color={color}]{t}[/color]"
