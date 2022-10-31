"""Entry widget for code."""

import math
from .. import kivy as kv
from kivy.core.text import Label, DEFAULT_FONT
from kivy.cache import Cache
from ..util import XWidget


Cache.register('kex.codeentry.label', timeout=60.)
cache_append = Cache.append
cache_get = Cache.get
cache_remove = Cache.remove


LABEL_KW = {
    'anchor_x': 'left',
    'anchor_y': 'top',
    'padding_x': 0,
    'padding_y': 0,
}


class XCodeEntryNew(kv.FocusBehavior, XWidget, kv.Widget):
    font_size = kv.NumericProperty(20)
    font = kv.StringProperty(DEFAULT_FONT)
    line_height = kv.NumericProperty(20)
    top_line = kv.NumericProperty(0)
    bottom_line = kv.NumericProperty(0)
    visible_lines = kv.NumericProperty(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._lines = [""]
        self._rects = [kv.Rectangle()]
        self._cursor_graphic = Cursor()
        # self.add(self._cursor_graphic)
        self._refresh_text()

    def insert_text(self, text: str):
        if text is None:
            return
        print(f"inserting text: {text!r}")
        if text == "\n":
            self._lines.append("")
            self._rects.append(kv.Rectangle())
        else:
            self._lines[-1] += text
        self._refresh_text()

    @property
    def label_kw(self):
        return LABEL_KW | {
            'font_size': self.font_size,
            'font_name': self.font,
        }

    def _refresh_text(self, *args):
        lines = self._lines
        rects = self._rects
        kw = self.label_kw
        for line_num, line in enumerate(lines):
            label = Label(text=line, **kw)
            label.refresh()
            texture = label.texture
            rects[line_num] = kv.Rectangle(texture=texture, size=texture.size)
        self._update_graphics()

    def _update_graphics(self, *args):
        self.canvas.clear()
        lines = self._lines
        rects = self._rects
        last_line = len(lines)
        line_height = self.line_height
        visible_lines = math.ceil(self.height / line_height)
        top_line = self.top_line
        bottom_line = min(top_line + visible_lines, last_line)
        canvas_add = self.canvas.add
        top, x = self.top, self.x
        for line_num in range(top_line, bottom_line):
            print(f"updating {line_num=}: {lines[line_num]!r}")
            rect = rects[line_num]
            canvas_add(rects[line_num])
            y = top - line_height - line_num * line_height
            rect.pos = x, y

    def on_focus(self, w, focus):
        self._cursor_graphic.blink = focus

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if super().on_touch_down(touch):
            return True
        print(f"touch down {touch.pos}")
        touch.grab(self)
        self._cursor_graphic.blink = False
        self._cursor_graphic.pos = touch.pos
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return
        self._cursor_graphic.pos = touch.pos
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return
        print(f"touch up   {touch.pos}")
        self._cursor_graphic.blink = True
        self._cursor_graphic.pos = touch.pos
        touch.ungrab(self)
        return True

    def keyboard_on_textinput(self, *args):
        print(f"XCodeEntry KB_text:     {args}")
        # return super().keyboard_on_textinput(*args)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        print(f"XCodeEntry KB_down:     {keycode=}, {text=}, {modifiers=}")
        keycode, keyname = keycode
        if "ctrl" in modifiers:
            return True
        if keycode == 13:  # enter
            text = "\n"
        self.insert_text(text)
        # return super().keyboard_on_key_down(window, keycode, text, modifiers)

    def keyboard_on_key_up(self, window, keycode):
        print(f"XCodeEntry KB_up:       {keycode=}")
        # return super().keyboard_on_key_up(window, keycode)


class Cursor(kv.Widget):
    blink = kv.BooleanProperty(True)
    color = kv.ListProperty([1, 1, 0, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__mid_blink = False
        with self.canvas:
            self.cursor_color = kv.Color(*self.color)
            self.cursor_graphic = kv.Rectangle(size=(3, 20))
            kv.Color()
        self._blink_ev = kv.Clock.create_trigger(
            self._do_cursor_blink, 0.5, interval=True,
        )
        self._blink_ev()

    def on_color(self, w, color):
        self.cursor_color.rgba = color

    def on_pos(self, w, pos):
        self.cursor_graphic.pos = self.to_widget(*pos)

    def on_blink(self, w, blink):
        self.__mid_blink = True
        self._blink_ev()
        if not blink:
            self._blink_ev.cancel()

    def _do_cursor_blink(self, *args):
        if not self.blink:
            if not self.__mid_blink:
                return
        if self.__mid_blink:
            self.cursor_color.a = self.color[-1]
            self.__mid_blink = False
        else:
            self.cursor_color.a = 0
            self.__mid_blink = True
