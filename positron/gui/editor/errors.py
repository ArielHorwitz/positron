"""Code errors modal."""

from .. import kex as kx, UI_FONT_KW


class Errors(kx.FocusBehavior, kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.set_size(hx=0.85, hy=0.8)
        self.make_bg(kx.get_color("navy", v=0.2, a=0.9))
        # Widgets
        title = kx.Label(text="Code Errors", bold=True, **UI_FONT_KW)
        title.set_size(y=50)
        self.summary_label = kx.Label(
            halign="left",
            valign="top",
            fixed_width=True,
            color=kx.get_color("magenta").rgba,
            padding=(10, 10),
            **UI_FONT_KW,
        )
        self.scroll_frame = kx.Scroll(view=self.summary_label)
        # Assemble
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, self.scroll_frame)
        self.add(main_frame)
        self.bind(parent=self._on_parent)

    def get_errors(self, *args):
        self.summary_label.scroll_y = 1
        errors = self.container.code_editor.update_errors()
        if errors:
            summary = "\n".join((
                f"{error.line:>5},{error.column:>3} :: {error.message}"
                for error in errors
            ))
        else:
            summary = "No errors :)"
        self.summary_label.text = summary

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is not None:
            self.focus = True
            self.get_errors()

    def on_touch_down(self, touch):
        super().on_touch_down(touch)
        if self.collide_point(*touch.pos):
            touch.grab(self)
            return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True

    def keyboard_on_key_down(self, w, key, text, mods):
        keycode, key = key
        if keycode == 278:  # home
            self.scroll_frame.scroll_y = 1
        elif keycode == 279:  # end
            self.scroll_frame.scroll_y = 0
        elif keycode == 280:  # page up
            self.scroll_frame.scroll_up(count=10)
        elif keycode == 281:  # page down
            self.scroll_frame.scroll_down(count=10)
        elif keycode == 273:  # up arrow
            self.scroll_frame.scroll_up()
        elif keycode == 274:  # down arrow
            self.scroll_frame.scroll_down()
