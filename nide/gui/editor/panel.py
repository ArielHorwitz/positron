"""Code editor panel widget.

Contains the code editor and modals.
"""

from .. import kex as kx
from .code import CodeEditor
from .tree import ProjectTree


class Panel(kx.Anchor):
    def __init__(self, uid: int, session, file: str, **kwargs):
        super().__init__(**kwargs)
        self.__uid = uid
        self.im = kx.InputManager(name=f"Editor panel {uid}")
        self.code_editor = self.add(CodeEditor(session, uid, file))
        self.project_tree = ProjectTree(
            session=session,
            container=self,
            name=f"Project modal {uid}",
        )
        self.im.register(
            "Open project tree",
            self.project_tree.toggle,
            "^ o",
        )
        self.code_editor.code_entry.bind(focus=self._on_code_focus)
        self.project_tree.bind(parent=self._on_project_modal)
        self.set_focus = self.code_editor.code_entry.set_focus

    @property
    def file(self):
        return self.code_editor.file

    @property
    def uid(self):
        return self.__uid

    def _on_code_focus(self, w, focus):
        self.im.active = focus

    def _on_project_modal(self, w, parent):
        if parent is None:
            self.code_editor.set_focus()

    @property
    def load(self):
        return self.code_editor.load

    @property
    def reload(self):
        return self.code_editor.reload
