"""Modal for testing purposes."""

from loguru import logger
from pathlib import Path
import subprocess
from .. import kex as kx, UI_FONT_KW, UI_LINE_HEIGHT
from ...util import settings
from ...util.file import PROJ_DIR, open_path


TREE_TOP_PREFIX = "╚╦═ "
TREE_CHILD_PREFIX = " ╠═══ "
TREE_CHILD_PREFIX_LAST = " ╚═══ "
MISSING_COLOR = "#ff0000"
FOLDER_COLOR = "#0066ff"
FILE_COLOR = "#00ff66"
PARENT_COLOR = "#77aaff"


class Disk(kx.Modal):
    def __init__(self, session, **kwargs):
        self.session = session
        self._current_paths = []
        self._current_reprs = []
        self._create_bookmarks()
        super().__init__(**kwargs)
        self.set_size(hx=0.85, hy=0.8)
        self.make_bg(kx.get_color("yellow", v=0.1))
        title = kx.Label(text="Disk Browser", bold=True, **UI_FONT_KW)
        title.make_bg(kx.get_color("orange", v=0.3))
        title.set_size(y=UI_LINE_HEIGHT * 2)
        help_label = kx.Label(halign="left", italic=True, **UI_FONT_KW)
        self.tree_list = kx.List(item_height=UI_LINE_HEIGHT, **UI_FONT_KW)
        # Assemble
        widget_frame = kx.Anchor(anchor_y="top")
        widget_frame.add(self.tree_list)
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, widget_frame, help_label)
        self.add(main_frame)
        # Events
        self._trigger_refresh_items = kx.create_trigger(self._refresh_items, timeout=.1)
        self.bind(parent=self._on_parent)
        self.tree_list.bind(on_invoked=self._on_invoked)
        self.im.register("Browse back", self._browse_back, "backspace")
        self.im.register("Browse bookmarks", self._browse_bookmarks, "home")
        self.im.register("Browse project", self._browse_project, "^ home")
        self.im.register("Open path", self._open_path, ["^ enter", "^ numpadenter"])
        self.im.register(
            "Explore path",
            self._explore_path,
            ["^+ enter", "^+ numpadenter"],
        )
        help_label.text = "\n".join([
            "           [u]backspace[/u] : back",
            "                [u]home[/u] : bookmarks",
            "         [u]ctrl + home[/u] : project folder",
            "        [u]ctrl + enter[/u] : open in a new window",
            "[u]ctrl + shift + enter[/u] : open in explorer",
        ])
        help_label.set_size(y=UI_LINE_HEIGHT * 5)
        self._browse_bookmarks()
        settings.bind("project.bookmarks", self._create_bookmarks)

    def _create_bookmarks(self, *args):
        paths = [None]
        reprs = [_wrap_color("BOOKMARKS", PARENT_COLOR)]
        # User defind bookmarks
        for bm in settings.get("project.bookmarks"):
            file, name = bm, None
            if ";" in bm:
                file, name = bm.rsplit(";")
            p = Path(file).expanduser().resolve()
            if not name:
                name = self._path_repr(p, name_only=False)
            paths.append(p)
            reprs.append(_wrap_color(name, _get_color(p)))
        paths.append(self.session.dir_tree.root)
        reprs.append(_wrap_color("Project folder", FOLDER_COLOR))
        self._bookmark_paths = paths
        self._bookmark_reprs = reprs

    def _set_dir(self, path: Path):
        while not path.exists() or not path.is_dir():
            path = path.parent
        children = self._get_children(path)
        paths = [path.parent, *children]
        parent_repr = self.session.repr_full_path(path)
        reprs = [_wrap_color(kx.escape_markup(parent_repr), PARENT_COLOR)]
        reprs.extend(self._path_repr(c, name_only=True) for c in children)
        self._current_paths = paths
        self._current_reprs = reprs
        self._trigger_refresh_items()

    def _browse_bookmarks(self, *args):
        self._current_paths = self._bookmark_paths
        self._current_reprs = self._bookmark_reprs
        self._trigger_refresh_items()

    def _refresh_items(self, *args):
        reprs = self._current_reprs
        items = [f"{TREE_TOP_PREFIX}{reprs[0]}"]
        if len(reprs) > 1:
            items.extend(f"{TREE_CHILD_PREFIX}{r}" for r in reprs[1:-1])
            items.append(f"{TREE_CHILD_PREFIX_LAST}{reprs[-1]}")
        self.tree_list.items = items

    def _browse_back(self, *args):
        p = self._current_paths[0]
        if p is not None:
            self._set_dir(p)

    def _browse_project(self, *args):
        self._set_dir(self.session.dir_tree.root)

    def _on_invoked(self, w, index: int, label: str):
        path = self._current_paths[index]
        logger.debug(f"Invoked {path=}")
        if path.is_dir():
            self._set_dir(path)
        else:
            self.container.load(path)
            self.dismiss()

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is None:
            return
        self.tree_list.set_focus()
        self._trigger_refresh_items()

    def _open_path(self, *args):
        path = self._current_paths[self.tree_list.selection]
        if not path.exists():
            logger.debug(f"No such path: {path}")
            return
        logger.info(f"Opening path: {path}")
        command_args = [str(PROJ_DIR / "run-positron.sh"), str(path)]
        proc = subprocess.Popen(command_args)
        logger.debug(f"{proc=}")

    def _explore_path(self, *args):
        path = self._current_paths[self.tree_list.selection]
        if not path.exists():
            logger.debug(f"No such path: {path}")
            return
        logger.info(f"Exploring path: {path}")
        open_path(path)

    def _get_children(self, path: Path):
        func = self.session.dir_tree.get_children_from_disk
        return func(path, use_file_types=False, use_path_filter=False)

    def _path_repr(self, p: Path, name_only: bool) -> str:
        name = p.name if name_only else self.session.repr_full_path(p)
        if p.is_dir():
            color = FOLDER_COLOR
            name = f"{name}/"
        elif p.is_file():
            color = FILE_COLOR
        else:
            color = MISSING_COLOR
        return _wrap_color(name, color)


def _get_color(p: Path) -> str:
    if p.is_dir():
        return FOLDER_COLOR
    elif p.is_file():
        return FILE_COLOR
    return MISSING_COLOR


def _wrap_color(t, color):
    return f"[color={color}]{t}[/color]"
