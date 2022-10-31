"""Modal for testing purposes."""

from .. import kex as kx, FONTS_DIR
from ...util import settings


FONT = str(FONTS_DIR / settings.get("editor.font"))
FONT_SIZE = settings.get("editor.font_size")
UI_FONT_SIZE = settings.get("ui.font_size")


class Test(kx.Modal):
    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.set_size(hx=0.85, y=500)
        self.make_bg(kx.get_color("purple", v=0.1))
        title = kx.Label(text="Test")
        title.make_bg(kx.get_color("orange", v=0.3))
        title.set_size(y=50)
        self.code = kx.CodeEntryNew(font=FONT)
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, self.code)
        self.add(main_frame)
        self.bind(parent=self._on_parent)

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is None:
            return
        self.code.set_focus()
