"""Goto dialog for line number in code editor."""

from .. import kex as kx, FONTS_DIR
from ...util import settings

FONT = str(FONTS_DIR / settings.get("editor.font"))
UI_FONT_SIZE = settings.get("ui.font_size")


class Goto(kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.set_size(x=200, y=100)
        title = kx.Label(text="Goto line number")
        title.make_bg(kx.get_color("black", a=0.5))
        self.line_number_entry = kx.CodeEntry(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            select_on_focus=True,
            write_tab=False,
            text_validate_unfocus=False,
            style_name="solarized-dark",
            background_color=kx.XColor(0.12, 0.04, 0.2, 0.5).rgba,
            multiline=False,
            halign="center",
        )
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, self.line_number_entry)
        self.add(main_frame)
        self.bind(parent=self._on_parent)
        self.im.register("Goto line", self.goto, "enter")
        self.im.register("Goto line (2)", self.goto, "numpadenter")
        self.im.register("Goto line end", self.goto_end, "+ enter")
        self.im.register("Goto line end (2)", self.goto_end, "+ numpadenter")

    def goto(self, *args, end: bool = False):
        line_num = self.line_number_entry.text
        try:
            line_num = max(1, int(line_num))
        except ValueError:
            print(f"Cannot use {line_num!r} as a line number.")
            return
        self.container.code_editor.goto_line(line_num, end=end)
        self.dismiss()

    def goto_end(self, *args):
        self.goto(*args, end=True)

    def find_prev(self, *args):
        self.container.code_editor.find_prev(self.line_number_entry.text)
        self.dismiss()

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is not None:
            selected_text = self.container.code_editor.selected_text
            if selected_text:
                self.line_number_entry.text = selected_text
            self.line_number_entry.focus = True
