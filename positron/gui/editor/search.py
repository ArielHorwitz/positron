"""Project search."""

from loguru import logger
from .. import kex as kx, UI_FONT_KW, UI_CHAR_WIDTH, UI_LINE_HEIGHT
from ...util import settings
from ...util.file import file_load, search_text


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
        self.title = kx.Label(text="Search Project", bold=True, **UI_FONT_KW)
        self.title.set_size(y=UI_LINE_HEIGHT)

        # Search
        self.search_entry = kx.Entry(
            halign="center",
            write_tab=False,
            select_on_focus=True,
            text_validate_unfocus=False,
            background_color=(0.04, 0.12, 0.2, 1),
            multiline=False,
            **UI_FONT_KW,
        )
        self.search_entry.set_size(y=UI_LINE_HEIGHT + self.search_entry.padding[1] * 2)
        self.search_entry.bind(text=self._on_search_text)

        # Tree
        self.results_list = kx.List(
            on_invoke=self._on_invoke,
            shorten=False,
            item_height=UI_LINE_HEIGHT * 3,
            **UI_FONT_KW,
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
            settings.get("project.text_search_cooldown"),
        )
        settings.bind("project.text_search_cooldown", self._refresh_search_cooldown)
        self.bind(parent=self._on_parent)
        self.im.register("Load", self._do_load, ["enter", "numpadenter"])
        self.im.register("Focus ", self._on_down_arrow, "down")

    def _refresh_search_cooldown(self, *args):
        self._refresh_results.timeout = settings.get("project.text_search_cooldown")

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
                max_results=settings.get("project.max_search_results"),
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
        line_width = int(self.results_list.width / UI_CHAR_WIDTH)
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
        selected_text = self.container.code_editor.selected_text
        if selected_text:
            self.search_entry.text = selected_text
        self.search_entry.focus = True
        self._on_search_text()


def _wrap_color(t, color):
    return f"[color={color}]{t}[/color]"
