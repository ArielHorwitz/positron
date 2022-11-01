"""Snippets dialog for inserting preset text in code editor."""

import shutil
from .. import kex as kx, FONTS_DIR
from ...util import settings
from ...util.snippets import find_snippets


FONT = str(FONTS_DIR / settings.get("editor.font"))
UI_FONT_SIZE = settings.get("ui.font_size")


class Snippets(kx.Modal):
    snippets = kx.ListProperty()

    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.set_size(hx=0.85, hy=0.8)
        self.make_bg(kx.get_color("lime", a=0.75))
        # Widgets
        title = kx.Label(text="Insert snippet")
        title.set_size(y=50)
        self.snippet_entry = kx.Entry(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            select_on_focus=True,
            write_tab=False,
            text_validate_unfocus=False,
            background_color=kx.XColor(0.12, 0.04, 0.2, 0.5).rgba,
            multiline=False,
        )
        self.snippet_label = kx.Label(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            halign="left",
            valign="top",
        )

        # Assemble
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, self.snippet_entry, self.snippet_label)
        self.add(main_frame)
        self.bind(parent=self._on_parent)
        self.im.register("Insert snippet", self.insert_snippet, "enter")
        self.im.register("Insert snippet (2)", self.insert_snippet, "numpadenter")
        self.snippet_entry.bind(text=self._on_entry_text)
        self._on_entry_text(None, "")

    def insert_snippet(self, *args):
        if not self.snippets:
            return
        self.container.code_editor.insert_snippet(self.snippets[0])
        self.dismiss()

    def _on_entry_text(self, w, text):
        self.snippets = find_snippets(text)

    def on_snippets(self, w, snippets):
        self.snippet_label.text = "\n".join(
            f"{s.name:<15} {s.text[:50]!r}"
            for s in snippets
        )

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is not None:
            self.snippet_entry.text = ""
            self.snippet_entry.focus = True
