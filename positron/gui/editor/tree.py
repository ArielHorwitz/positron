"""Project tree for listing and opening files."""

from loguru import logger
import arrow
from pathlib import Path
import fuzzysearch
from .. import kex as kx, UI_FONT_KW, UI_LINE_HEIGHT
from ...util import settings


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
        self.title = kx.Label(**UI_FONT_KW)
        self.title.set_size(y=UI_LINE_HEIGHT * 2)

        # Quick results
        self.quick_label = kx.Label(bold=True, **UI_FONT_KW)
        self.quick_label.set_size(y=UI_LINE_HEIGHT)

        # Search
        self.search_entry = kx.Entry(
            halign="center",
            background_color=kx.XColor(0.2, 0.6, 1, v=0.2).rgba,
            select_on_focus=True,
            multiline=False,
            **UI_FONT_KW,
        )
        self.search_entry.set_size(y=UI_LINE_HEIGHT + self.search_entry.padding[1] * 2)
        self.search_entry.bind(text=self._on_search_text)

        # Tree
        self.tree_list = kx.List(item_height=UI_LINE_HEIGHT, **UI_FONT_KW)
        help_label = kx.Label(halign="left", italic=True, **UI_FONT_KW)

        # Assemble
        self.search_entry.focus_next = self.tree_list
        self.tree_list.focus_next = self.search_entry
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(
            self.title,
            self.quick_label,
            self.search_entry,
            self.tree_list,
            help_label,
        )
        self.add(main_frame)
        self._refresh_title()

        # Events
        self._refresh_tree = kx.snoozing_trigger(
            self._do_refresh_tree,
            settings.get("project.tree_search_cooldown"),
        )
        self._do_refresh_tree()
        settings.bind("project.tree_search_cooldown", self._refresh_settings)
        self.bind(parent=self._on_parent)
        self.im.register("Load", self._on_enter, ["enter", "numpadenter"])
        self.im.register("New", self._on_enter_new, ["^ enter", "^ numpadenter"])
        self.im.register("Focus tree", self._on_down, "down")
        self.im.register("Project root", self._clear_search, "home")
        help_label.text = "\n".join([
            "                [u]home[/u] : project root",
            "        [u]ctrl + enter[/u] : force open / create new file",
        ])
        help_label.set_size(y=UI_LINE_HEIGHT * 2)

    def _refresh_settings(self):
        self._refresh_tree.timeout = settings.get("project.tree_search_cooldown")

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
        get_icon = self.session.get_path_icon
        items = [str(root)]
        self._quick_file = None
        self._files = self._get_tree_files()
        self.quick_label.text = f"{root}/..."
        if self._files:
            items = []
            append = items.append
            for f in self._files:
                path_str = kx.escape_markup(f"{get_icon(f)} $/{f.relative_to(root)}")
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
        fuzzy_ldist = settings.get("project.tree_search_fuzziness")
        if pattern:
            files = []
            append = files.append
            for path in all_paths:
                path_str = str(path.relative_to(root)).lower()
                if do_fuzzy:
                    match = fuzzysearch.find_near_matches(
                        pattern,
                        path_str,
                        max_l_dist=fuzzy_ldist,
                        max_deletions=0,
                        max_insertions=fuzzy_ldist,
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
            f"[b]Project Tree: {file_count}[/b] files{fuzzy_warn}\n"
            f"[i]{self.dtree.root}[/i]"
        )

    @property
    def fuzzy_enabled(self):
        threshold = settings.get("project.tree_fuzzy_threshold_count")
        return len(self.dtree.all_paths) <= threshold

    def _clear_search(self, *args):
        self.search_entry.text = ""
        self.search_entry.focus = True


def _wrap_color(t, color):
    return f"[color={color}]{t}[/color]"
