"""Project tree for listing and opening files."""

from pathlib import Path
from itertools import islice, chain
from .. import kex as kx, FONTS_DIR
from ...util import settings
from ...util.file import format_dir_tree, search_files


FONT = str(FONTS_DIR / settings.get("editor.font"))
UI_FONT_SIZE = settings.get("ui.font_size")
BREADTH_FIRST = settings.get("project.breadth_first")
DIR_TREE_DEPTH = settings.get("project.tree_depth")
FILE_TYPES = set(settings.get("project.file_types"))
IGNORE_NAMES = set(settings.get("project.ignore_names"))
IGNORE_MATCHES = set(settings.get("project.ignore_match"))
GLOBAL_DIRS = [
    Path(p).expanduser().resolve()
    for p in settings.get("project.global_folders")
]
GLOBAL_FILES = [
    Path(p).expanduser().resolve()
    for p in settings.get("project.global_files")
]
MAX_FILES = settings.get("project.max_tree_size")


class ProjectTree(kx.Modal):
    files = kx.ListProperty()

    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.set_size(hx=0.8, hy=0.8)
        self.make_bg(kx.get_color("cyan", v=0.2))
        self.title = kx.Label(text="Project Tree")
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
        self.tree_label = kx.Label(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            halign="left",
            valign="top",
        )

        # Assemble
        panel_frame = kx.Box(orientation="vertical")
        panel_frame.add(self.search_entry, self.tree_label)
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(self.title, panel_frame)
        self.add(main_frame)

        # Events
        self.bind(parent=self._on_parent, files=self._on_files)
        self.search_entry.bind(focus=self._on_search_focus)
        self._on_search_text(self.search_entry, "")
        self.im.register("Load", self._do_load, "enter")
        self.im.register("Load (2)", self._do_load, "numpadenter")
        self.im.register("New", self._do_new, "^ enter")
        self.im.register("New (2)", self._do_new, "^ numpadenter")
        self.im.register("Scroll down", self._scroll_down, "down", allow_repeat=True)
        self.im.register("Scroll up", self._scroll_up, "up", allow_repeat=True)
        self.im.register("Page down", lambda: self._scroll_down(10), "pagedown", allow_repeat=True)
        self.im.register("Page up", lambda: self._scroll_up(10), "pageup", allow_repeat=True)

    def _do_new(self):
        self._do_load(force_new=True)

    def _do_load(self, force_new: bool = False):
        if not self.files or force_new:
            file = self.session.project_path / Path(self.search_entry.text)
        else:
            file = self.files[0]
        self.container.load(file)
        self.toggle(set_as=False)

    def _scroll_down(self, count=1):
        for i in range(count):
            self.files.append(self.files.pop(0))

    def _scroll_up(self, count=1):
        for i in range(count):
            self.files.insert(0, self.files.pop())

    def _on_files(self, w, files):
        project_path = self.session.project_path
        self.tree_label.text = format_dir_tree(files, relative_dir=project_path)

    def _on_search_text(self, w, text):
        gens = []
        for directory in [self.session.project_path] + GLOBAL_DIRS:
            gens.append(search_files(
                dir=directory,
                pattern=text,
                ignore_names=IGNORE_NAMES,
                ignore_matches=IGNORE_MATCHES,
                file_types=FILE_TYPES,
                breadth_first=BREADTH_FIRST,
                depth=DIR_TREE_DEPTH,
            ))
        gens.append((p for p in GLOBAL_FILES if text in str(p)))
        self.files = list(islice(chain(*gens), MAX_FILES))

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
