"""Code editor panel widget.

Contains the code editor and modals.
"""

from .. import kex as kx
from .code import CodeEditor
from .tree import ProjectTree
from .find import Find


class Panel(kx.Anchor):

    modal = kx.ObjectProperty(None)

    def __init__(self, uid: int, session, file: str, **kwargs):
        super().__init__(**kwargs)
        self.__uid = uid
        self.im = kx.InputManager(name=f"Editor panel {uid}", active=False)
        # Code
        self.code_editor = self.add(CodeEditor(session, uid, file))
        self.set_focus = self.code_editor.set_focus
        self.code_editor.code_entry.bind(focus=self._on_code_focus)
        # Modals
        self.project_tree = ProjectTree(
            session=session,
            container=self,
            name=f"Tree modal {uid}",
        )
        self.find_replace = Find(
            session=session,
            container=self,
            name=f"Find modal {uid}",
        )
        self.modals = {
            "tree": self.project_tree,
            "find": self.find_replace,
        }
        modal_hotkeys = {"tree": "^ t", "find": "^ f"}
        for name, modal in self.modals.items():
            modal.bind(parent=self._on_modal)
            hk = modal_hotkeys.get(name)
            if hk:
                self.im.register(f"Toggle {name} modal", modal.toggle, hk)

    def _on_modal(self, modal, parent):
        assert parent is self or parent is None
        # Reset focus if modal closed
        if parent is None:
            self.code_editor.set_focus()
        # Remember modal and dismiss others
        self.modal = modal
        for m_ in self.modals.values():
            if m_ is not modal:
                m_.dismiss()

    def _on_code_focus(self, w, focus):
        self.im.active = focus

    @property
    def file(self):
        return self.code_editor.file

    @property
    def uid(self):
        return self.__uid

    @property
    def load(self):
        return self.code_editor.load

    @property
    def reload(self):
        return self.code_editor.reload
