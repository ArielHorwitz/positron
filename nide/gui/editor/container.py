"""Container for code editor panels."""

from pathlib import Path
from .. import kex as kx
from ...util import settings
from .panel import Panel


LAYOUT_COLS = settings.get("ui.cols")
LAYOUT_ROWS = settings.get("ui.rows")
DEFAULT_FILES = settings.get("project.open")
MAX_EDITOR_HOTKEYS = 4


class Container(kx.Anchor):

    current_focus = kx.NumericProperty(None)

    def __init__(self, session):
        super().__init__()
        self.im = kx.InputManager(name="Panel container")
        self.session = session
        # Collect files to open
        open_files = self.session.get_session_files()
        if not open_files:
            open_files = DEFAULT_FILES
        files = [self.session.project_path / Path(file) for file in open_files]
        # Create widgets
        self.editors = []
        for i in range(LAYOUT_COLS * LAYOUT_ROWS):
            file = files.pop(0) if files else None
            self.editors.append(Panel(i, self.session, file))
        # Assemble
        main_frame = kx.Grid(cols=LAYOUT_COLS, rows=LAYOUT_COLS)
        main_frame.add(*self.editors)
        self.add(main_frame)
        self.editors[0].set_focus()
        self.register_hotkeys()
        self.app.bind(current_focus=self._check_focus)

    def _check_focus(self, w, current_focus):
        panel = current_focus
        while panel:
            if isinstance(panel, Panel):
                assert self._check_descendent(panel)
                self.current_focus = panel.uid
                print(f"Focused panel uid: {self.current_focus}")
                return
            if panel is kx.Window.kivy:
                break
            panel = panel.parent
        return

    def _check_descendent(self, widget):
        while widget:
            if widget is self:
                return True
            widget = widget.parent
        return False

    def register_hotkeys(self):
        self.im.remove_all()
        for editor in self.editors[:MAX_EDITOR_HOTKEYS]:
            self.im.register(
                f"Focus Editor {editor.uid}",
                editor.set_focus,
                f"f{editor.uid+1}",
            )
        self.im.register("Reload all", self.reload_all, "f5")

    def reload_all(self):
        for editor in self.editors:
            editor.reload()

    def clean_up(self):
        files = [editor.file for editor in self.editors]
        self.session.save_session_files(files)
