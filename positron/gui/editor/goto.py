"""Goto dialog for line number in code editor."""

from loguru import logger
from .. import kex as kx, UI_FONT_KW, UI_LINE_HEIGHT


class Goto(kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.set_size(hx=0.5, y=UI_LINE_HEIGHT * 3)
        title = kx.Label(text="Goto line", bold=True, **UI_FONT_KW)
        title.make_bg(kx.get_color("black", a=0.5))
        self.line_number_entry = kx.CodeEntry(
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
        main_frame.add(title, self.line_number_entry)
        self.add(main_frame)
        self.bind(parent=self._on_parent)
        self.im.register("Goto line", self.goto, ["enter", "numpadenter"])
        self.im.register(
            "Goto line start",
            self.goto_start,
            ["+ enter", "+ numpadenter"],
        )

    def goto(self, *args, end: bool = True):
        line_num = self.line_number_entry.text
        try:
            line_num = max(1, int(line_num))
        except ValueError:
            logger.warning(f"Cannot use {line_num!r} as a line number.")
            return
        column = 10 ** 6 if end else 0
        self.container.code_editor.set_cursor(line_num, column)
        self.dismiss()

    def goto_start(self, *args):
        self.goto(*args, end=False)

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
