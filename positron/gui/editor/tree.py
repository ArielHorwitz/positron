"""Project tree for listing and opening files."""

from loguru import logger
import arrow
from pathlib import Path
import fuzzysearch
from .. import kex as kx, FONTS_DIR
from ...util import settings


FONT = str(FONTS_DIR / settings.get("ui.font"))
UI_FONT_SIZE = settings.get("ui.font_size")
REFRESH_DELAY = settings.get("project.tree_search_cooldown")
FUZZY_LDIST = settings.get("project.tree_search_fuzziness")
FUZZY_THRESHOLD_COUNT = settings.get("project.tree_fuzzy_threshold_count")
CHAR_SIZE = kx.CoreLabel(font=FONT, font_size=UI_FONT_SIZE).get_extents(text="a")
CHAR_WIDTH, LINE_HEIGHT = CHAR_SIZE
MISSING_COLOR = "#ff0000"
FOLDER_COLOR = "#0066ff"
FILE_COLOR = "#00ff66"
QUICK_FILE_COLOR = "#00ffff"


class ProjectTree(kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self._last_modified = self.dtree.last_modified.shift(seconds=-1)
        self._quick_file = None
        self.set_size(hx=0.8, hy=0.9)
        self.make_bg(kx.get_color("cyan", v=0.2))
        self.title = kx.Label(font_name=FONT, font_size=UI_FONT_SIZE)
        self.title.set_size(y=LINE_HEIGHT * 3)

        # Quick results
        self.quick_label = kx.Label(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
        )
        self.quick_label.set_size(y=40)

        # Search
        self.search_entry = kx.Entry(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            halign="center",
            background_color=kx.XColor(0.2, 0.6, 1, v=0.2).rgba,
            select_on_focus=True,
            multiline=False,
        )
        self.search_entry.set_size(y=40)
        self.search_entry.bind(text=self._on_search_text)

        # Tree
        self.tree_list = kx.List(
            item_height=LINE_HEIGHT,
            font_name=FONT,
            font_size=UI_FONT_SIZE,
        )

        # Assemble
        self.search_entry.focus_next = self.tree_list
        self.tree_list.focus_next = self.search_entry
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(
            self.title,
            self.quick_label,
            self.search_entry,
            self.tree_list,
        )
        self.add(main_frame)
        self._refresh_title()

        # Events
        self._refresh_tree = kx.snoozing_trigger(self._do_refresh_tree, REFRESH_DELAY)
        self._do_refresh_tree()
        self.bind(parent=self._on_parent)
        self.im.register("Load", self._on_enter, "enter")
        self.im.register("Load (2)", self._on_enter, "numpadenter")
        self.im.register("New", self._on_enter_new, "^ enter")
        self.im.register("New (2)", self._on_enter_new, "^ numpadenter")
        self.im.register("Focus tree", self._on_down, "down")

    @property
    def dtree(self):
        return self.session.dir_tree

    def _do_load(self, file: Path):
        self.container.load(file)
        self.dismiss()

    # Events
    def _on_enter(self):
        if self.search_entry.focus:
            if self._quick_file:
                self._do_load(self._quick_file)
        elif self.tree_list.focus and self._files:
            idx = self.tree_list.selection
            file = self._files[idx]
            if file.is_file():
                self._do_load(file)
            elif file.is_dir():
                self.search_entry.text = str(file.relative_to(self.dtree.root))

    def _on_enter_new(self):
        if self.search_entry.focus:
            file = self.dtree.root / Path(self.search_entry.text)
            self._do_load(file)

    def _on_down(self, *args):
        if self.search_entry.focus:
            self.tree_list.focus = True
        else:
            self.tree_list.select(delta=1)

    def _on_search_text(self, w, pattern):
        self._refresh_tree()

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is None:
            return
        self.search_entry.set_focus()
        self.dtree.reindex()
        self._refresh_tree()

    def _do_refresh_tree(self, *args):
        root = self.dtree.root
        items = [str(root)]
        self._quick_file = None
        self._files = self._get_tree_files()
        self.quick_label.text = f"{root}/..."
        if self._files:
            items = []
            append = items.append
            for f in self._files:
                path_str = kx.escape_markup(f"$/{f.relative_to(root)}")
                color = MISSING_COLOR
                if f.is_dir():
                    color = FOLDER_COLOR
                elif f.is_file():
                    color = FILE_COLOR
                    if self._quick_file is None:
                        self._quick_file = f
                        self.quick_label.text = _wrap_color(path_str, QUICK_FILE_COLOR)
                append(_wrap_color(path_str, color))
        self.tree_list.items = items
        self.tree_list.selection = 0
        self._refresh_title()

    def _get_tree_files(self, *args):
        logger.debug(f"Tree modal refreshing files from {self.dtree} {arrow.now()}")
        root = self.dtree.root
        pattern = self.search_entry.text.lower()
        files = all_paths = self.dtree.all_paths
        do_fuzzy = self.fuzzy_enabled
        if pattern:
            files = []
            append = files.append
            for path in all_paths:
                path_str = str(path.relative_to(root)).lower()
                if do_fuzzy:
                    match = fuzzysearch.find_near_matches(
                        pattern,
                        path_str,
                        max_l_dist=FUZZY_LDIST,
                        max_deletions=0,
                        max_insertions=FUZZY_LDIST,
                        max_substitutions=0,
                    )
                else:
                    match = pattern in path_str
                if match:
                    append(path)
        return sorted(files, key=self.dtree.sort_folders_key)

    def _refresh_title(self):
        if self.dtree.last_modified == self._last_modified:
            return
        self._last_modified = self.dtree.last_modified
        file_count = sum(p.is_file() for p in self.dtree.all_paths)
        fuzzy_warn = "" if self.fuzzy_enabled else " (no fuzzy search)"
        self.title.text = (
            f"[u]Project Tree:[/u] {file_count} files{fuzzy_warn}\n{self.dtree.root}"
        )

    @property
    def fuzzy_enabled(self):
        return len(self.dtree.all_paths) <= FUZZY_THRESHOLD_COUNT


def _wrap_color(t, color):
    return f"[color={color}]{t}[/color]"
