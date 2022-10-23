"""GUI panels."""

from pathlib import Path
from . import kex as kx
from ..util import settings
from .editor.editor import EditorPanel


EDITOR_COUNT = settings.get("ui.editors")
DEFAULT_FILES = settings.get("project.open")


class PanelContainer(kx.Anchor):
    def __init__(self, session):
        super().__init__()
        self.im = kx.InputManager(name="Panel container")
        self.session = session
        # Collect files to open
        open_files = self.session.get_session_files()
        if not open_files:
            open_files = DEFAULT_FILES
        files = [self.session.project_path / Path(file) for file in open_files]
        # Collect number of files
        editor_count = EDITOR_COUNT
        kw = {"cols": editor_count}
        if editor_count > 3:
            editor_count += editor_count % 2
            kw = {"rows": 2}
        # Create widgets
        self.editors = []
        for i in range(editor_count):
            file = files.pop(0) if files else None
            self.editors.append(EditorPanel(i, self.session, file))
        main_frame = kx.Grid(**kw)
        main_frame.add(*self.editors)
        self.add(main_frame)
        self.editors[0].set_focus()
        self.register_hotkeys()

    def register_hotkeys(self):
        self.im.remove_all()
        for editor in self.editors:
            self.im.register(
                f"Focus Editor {editor.uid}",
                editor.set_focus,
                f"f{editor.uid+1}",
            )
        self.im.register("Reload all", self.reload_all, "f5")

    def reload_all(self):
        for editor in self.editors:
            editor.load(reset_cursor=False)

    def clean_up(self):
        files = [editor.file for editor in self.editors]
        self.session.save_session_files(files)
