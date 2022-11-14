"""Find dialog for searching text in code editor."""

from .. import kex as kx, UI_FONT_KW, UI_LINE_HEIGHT


class Find(kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.set_size(hx=0.85, y=UI_LINE_HEIGHT * 3)
        title = kx.Label(text="Find", bold=True, **UI_FONT_KW)
        title.make_bg(kx.get_color("black", a=0.5))
        self.pattern_entry = kx.CodeEntry(
            select_on_focus=True,
            write_tab=False,
            text_validate_unfocus=False,
            style_name="solarized-dark",
            background_color=kx.XColor(0.12, 0.04, 0.2, 0.75).rgba,
            multiline=False,
            halign="center",
            **UI_FONT_KW,
        )
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, self.pattern_entry)
        self.add(main_frame)
        self.bind(parent=self._on_parent)
        self.im.register(
            "Find next",
            self.find_next,
            ["enter", "numpadenter", "^ ]"],
        )
        self.im.register(
            "Find prev",
            self.find_prev,
            ["+ enter", "+ numpadenter", "^ ["],
        )

    def find_next(self, *args):
        self.container.code_editor.find_next(self.pattern_entry.text)
        self.dismiss()

    def find_prev(self, *args):
        self.container.code_editor.find_prev(self.pattern_entry.text)
        self.dismiss()

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is None:
            return
        selected_text = self.container.code_editor.selected_text
        if selected_text:
            self.pattern_entry.text = selected_text
        self.pattern_entry.focus = True
