"""Container for code editor panels."""

from loguru import logger
from pathlib import Path
from .. import kex as kx
from ...util import settings
from ...util.file import FileCursor
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
        panel_count = LAYOUT_COLS * LAYOUT_ROWS
        # Collect files to open
        fcs = self.session.get_file_cursors()
        if not fcs:
            for file in DEFAULT_FILES:
                if file.startswith("./"):
                    file = self.session.project_path / Path(file)
                else:
                    file = Path(file)
                fcs.append(FileCursor(file))
        while len(fcs) < panel_count:
            fcs.append(FileCursor(settings.SETTINGS_FILE))
        fcs = fcs[:panel_count]
        # Create widgets
        self.panels = []
        for i, fc in enumerate(fcs):
            panel = Panel(i, self, self.session, fc.file)
            panel.code_editor.set_cursor(*fc.cursor)
            self.panels.append(panel)
        # Assemble
        self.panel_frame = kx.Grid(cols=LAYOUT_COLS, rows=LAYOUT_ROWS)
        self.panel_frame.add(*self.panels)
        self.add(self.panel_frame)
        self.register_hotkeys()
        self.app.bind(current_focus=self._check_focus)
        kx.schedule_once(self.panels[0].set_focus)

    def _check_focus(self, w, current_focus):
        panel = current_focus
        while panel:
            if isinstance(panel, Panel):
                assert self._check_descendent(panel)
                puid = panel.uid
                if self.current_focus != puid:
                    logger.debug(f"Focused panel uid: {puid}")
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
        for panel in self.panels[:MAX_EDITOR_HOTKEYS]:
            self.im.register(
                f"Focus Editor {panel.uid}",
                panel.set_focus,
                f"f{panel.uid+1}",
            )
        self.im.register("Reload all", self.reload_all, "^ f5")

    def reload_all(self):
        for panel in self.panels:
            panel.reload()

    def clean_up(self):
        fcs = [
            FileCursor(panel.code_editor.file, panel.code_editor.cursor)
            for panel in self.panels
        ]
        self.session.save_file_cursors(fcs)
