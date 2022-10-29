"""Code editor panel widget.

Contains the code editor and modals.
"""

from .. import kex as kx
from .code import CodeEditor
from .tree import ProjectTree
from .find import Find
from .goto import Goto
from .snippets import Snippets
from .analysis import Analysis


class Panel(kx.Anchor):

    modal = kx.ObjectProperty(None)

    def __init__(self, uid: int, container, session, file: str, **kwargs):
        super().__init__(**kwargs)
        self.__uid = uid
        self.im = kx.InputManager(name=f"Editor panel {uid}", active=False)
        # Code
        self.code_editor = self.add(CodeEditor(session, uid, file))
        self.set_focus = self.code_editor.set_focus
        # Modals
        modals = [
            (ProjectTree, "tree", "^ t"),
            (Find, "find", "^ f"),
            (Goto, "goto", "^ g"),
            (Snippets, "snippets", "^ spacebar"),
            (Analysis, "analysis", "! a"),
        ]
        self.modals = {}
        for modal_cls, name, hotkey in modals:
            modal = modal_cls(
                session=session,
                container=self,
                name=f"{name} modal {uid}",
            )
            self.modals[name] = modal
            modal.bind(parent=self._on_modal)
            if hotkey:
                self.im.register(f"Toggle {name} modal", modal.toggle, hotkey)
        self.im.register("Reload", self.reload, "f5")
        container.bind(current_focus=self._on_panel_focus)

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

    def _on_panel_focus(self, w, uid):
        self.im.active = uid == self.__uid

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
