"""Find dialog for searching text in code editor."""

from .. import kex as kx


class Find(kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.set_size(hx=0.85, y=100)
        title = kx.Label(text="Find")
        title.make_bg(kx.get_color("black", a=0.5))
        self.pattern_entry = kx.CodeEntry(
            #font_name=FONT,
            #font_size=UI_FONT_SIZE,
            select_on_focus=True,
            write_tab=False,
            text_validate_unfocus=False,
            style_name="solarized-dark",
            background_color=kx.XColor(0.12, 0.04, 0.2, 0.5).rgba,
            multiline=False,
        )
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, self.pattern_entry)
        self.add(main_frame)
        self.bind(parent=self._on_parent)
        self.im.register("Find next", self.find_next, "enter")
        self.im.register("Find next (2)", self.find_next, "numpadenter")
        self.im.register("Find next (3)", self.find_next, "^ ]")
        self.im.register("Find prev", self.find_prev, "+ enter")
        self.im.register("Find prev (2)", self.find_prev, "+ numpadenter")
        self.im.register("Find prev (3)", self.find_prev, "^ [")

    def find_next(self, *args):
        self.container.code_editor.find_next(self.pattern_entry.text)
        self.dismiss()

    def find_prev(self, *args):
        self.container.code_editor.find_prev(self.pattern_entry.text)
        self.dismiss()

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is not None:
            self.pattern_entry.focus = True
