"""Container for code editor panels."""

from pathlib import Path
from .. import kex as kx
from ...util import settings
from ...util.file import FileCursor, USER_DIR
from .panel import Panel


LAYOUT_COLS = settings.get("ui.cols")
LAYOUT_ROWS = settings.get("ui.rows")
DEFAULT_FILES = [Path(f) for f in settings.get("project.open")]
MAX_EDITOR_HOTKEYS = 4


class Container(kx.Anchor):

    current_focus = kx.NumericProperty(None)

    def __init__(self, session):
        super().__init__()
        self.im = kx.InputManager(name="Panel container")
        self.session = session
        editor_count = LAYOUT_COLS * LAYOUT_ROWS
        # Collect files to open
        fcs = self.session.get_file_cursors()
        if not fcs:
            for file in DEFAULT_FILES:
                # Try resolving files as relative to project
                rel_file = self.session.project_path / file
                file = rel_file if rel_file.exists() else file
                fcs.append(FileCursor(file))
        while len(fcs) < editor_count:
            fcs.append(FileCursor(settings.SETTINGS_FILE))
        fcs = fcs[:editor_count]
        # Create widgets
        self.editors = []
        for i, fc in enumerate(fcs):
            panel = Panel(i, self, self.session, fc.file)
            panel.code_editor.set_cursor(*fc.cursor)
            self.editors.append(panel)
        # Assemble
        main_frame = kx.Grid(cols=LAYOUT_COLS, rows=LAYOUT_COLS)
        main_frame.add(*self.editors)
        self.add(main_frame)
        self.register_hotkeys()
        self.app.bind(current_focus=self._check_focus)
        kx.schedule_once(self.editors[0].set_focus)

    def _check_focus(self, w, current_focus):
        panel = current_focus
        while panel:
            if isinstance(panel, Panel):
                assert self._check_descendent(panel)
                puid = panel.uid
                if self.current_focus != puid:
                    print(f"Focused panel uid: {puid}")
                    self.current_focus = puid
                return
            if panel is panel.parent:
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
        self.im.register("Reload all", self.reload_all, "^ f5")

    def reload_all(self):
        for editor in self.editors:
            editor.reload()

    def clean_up(self):
        fcs = [
            FileCursor(editor.code_editor.file, editor.code_editor.cursor)
            for editor in self.editors
        ]
        self.session.save_file_cursors(fcs)
