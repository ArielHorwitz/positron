"""Code analysis modal."""

from loguru import logger
import traceback
from .. import kex as kx, UI_FONT_KW


class Analysis(kx.FocusBehavior, kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.set_size(hx=0.85, hy=0.8)
        self.make_bg(kx.get_color("navy", v=0.2, a=0.9))
        # Widgets
        title = kx.Label(text="Code analysis")
        title.set_size(y=50)
        self.analysis_label = kx.Label(
            halign="left",
            valign="top",
            fixed_width=True,
            color=(0.5, 1, 0, 1),
            **UI_FONT_KW,
        )
        self.analysis_scroll = kx.Scroll(view=self.analysis_label)
        # Assemble
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, self.analysis_scroll)
        self.add(main_frame)
        self.bind(parent=self._on_parent)

    def analyze(self, *args):
        file = self.container.code_editor.file
        code = self.container.code_editor.code_entry
        col, row = code.cursor
        try:
            info = self.session.get_info(file, code.text, row+1, col)
        except Exception as e:
            info = "Analysis failed!\nPlease see logs."
            logger.warning("".join(traceback.format_exception(e)))
        self.analysis_label.text = info
        self.analysis_label.scroll_y = 1

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is not None:
            self.focus = True
            self.analyze()

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
            self.analysis_scroll.scroll_y = 1
        elif keycode == 279:  # end
            self.analysis_scroll.scroll_y = 0
        elif keycode == 280:  # page up
            self.analysis_scroll.scroll_up(count=10)
        elif keycode == 281:  # page down
            self.analysis_scroll.scroll_down(count=10)
        elif keycode == 273:  # up arrow
            self.analysis_scroll.scroll_up()
        elif keycode == 274:  # down arrow
            self.analysis_scroll.scroll_down()
