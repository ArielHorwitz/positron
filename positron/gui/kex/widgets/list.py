"""List widget."""

from typing import Optional
from .. import kivy as kv
from ..util import text_texture
from .layouts import XRelative


OUTLINE = "atlas://data/images/defaulttheme/bubble_btn_pressed"
EMPTY_TEXTURE = text_texture(" ")

# Cache setup
kv.Cache.register("XList")
cache_append = kv.Cache.append
cache_get = kv.Cache.get
cache_remove = kv.Cache.remove


class XList(kv.FocusBehavior, XRelative):

    font = kv.StringProperty()
    font_size = kv.NumericProperty()
    item_height = kv.NumericProperty(35)
    items = kv.ListProperty()
    selection = kv.NumericProperty(0)
    paging_size = kv.NumericProperty(None)
    indicator_width = kv.NumericProperty(5)
    indicator_color = kv.ColorProperty([0.5, 0.5, 0.5, 0.5])
    # TODO implement bg colors
    bg_color = kv.ColorProperty([0.05, 0.075, 0.1, 1])
    bg_color_alt = kv.ColorProperty([0.05, 0.1, 0.075, 1])
    enable_shifting = kv.BooleanProperty(False)
    _label_kwargs = kv.DictProperty()

    def __init__(self, font: str, font_size: int, **kwargs):
        super().__init__(font=font, font_size=font_size, **kwargs)
        self._rects = []
        self._scroll = 0
        self.items = ["placeholder"]
        self._refresh_label_kwargs()
        self._create_other_graphics()
        self._refresh_graphics()
        self._refresh_selection_graphics()
        self.register_event_type("on_invoked")
        self.bind(
            focus=self._on_focus,
            items=self._on_items,
            scroll=self._on_scroll,
            size=self._on_geometry,
            pos=self._on_geometry,
            selection=self._on_selection,
            item_height=self._refresh_label_kwargs,
            font=self._refresh_label_kwargs,
            font_size=self._refresh_label_kwargs,
            indicator_color=self._refresh_scroll_indicator_color,
            _label_kwargs=self._on_label_kwargs,
        )

    def _on_items(self, w, items):
        assert len(self.items) > 0
        self.select()
        self._refresh_items()
        self._refresh_scroll_indicator()

    def _on_scroll(self, *args):
        self._refresh_items()
        self._refresh_scroll_indicator()

    def select(self, index: Optional[int] = None, /, *, delta: int = 0):
        if index is None:
            index = self.selection
        index += delta
        index = max(0, min(index, len(self.items) - 1))
        self.selection = index

    def set_scroll(self, index: Optional[int] = None, /, *, delta: int = 0):
        if index is None:
            index = self.scroll
        index += delta
        self.scroll = index

    def _on_selection(self, *args):
        self.set_scroll()
        self._refresh_selection_graphics()

    def _refresh_selection_graphics(self, *args):
        idx = self.selection
        offset = idx - self.scroll
        self._selection_rect.pos = self._get_rect_pos(offset)
        self._selection_rect.size = self._rects[offset].size

    def _refresh_scroll_indicator(self, *args):
        scroll = self.scroll
        rect_count = len(self._rects)
        item_count = len(self.items)
        widget_height = self.height
        indicator_width = self.indicator_width
        # Find relative scroll of indicator top and bottom edges
        indicator_rel_top = 1 - scroll / item_count
        indicator_rel_height = min(rect_count, item_count) / item_count
        indicator_rel_bot = max(0, indicator_rel_top - indicator_rel_height)
        # Adjust based on widget size
        indicator_height = widget_height * indicator_rel_height
        indicator_y = widget_height * indicator_rel_bot
        indicator_x = self.width - indicator_width
        # Sometimes we are asked to refresh when not all properties have finished
        # updating, let's gracefully handle that by pretending we see the entire list
        broken_geometry = (
            (not 0 <= indicator_rel_bot <= indicator_rel_top <= 1)
            or (not 0 <= indicator_rel_height <= 1)
        )
        if broken_geometry:
            indicator_height = widget_height
            indicator_y = 0
        self._scroll_indicator.pos = self.x + indicator_x, self.y + indicator_y
        self._scroll_indicator.size = indicator_width, indicator_height

    def _refresh_scroll_indicator_color(self, *args):
        self._scroll_indicator_color.rgba = self.indicator_color

    def _on_geometry(self, *args):
        self._bg.size = self.size
        self._bg.pos = self.pos
        self._refresh_label_kwargs()
        self._refresh_graphics()

    def _create_other_graphics(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            self._bg_color = kv.Color(0, 0.1, 0)
            self._bg = kv.Rectangle(size=(50, 50))
            kv.Color()
        self.canvas.after.clear()
        with self.canvas.after:
            self._selection_rect_color = kv.Color(0, 0.5, 0.5, 0.5)
            self._selection_rect = kv.Rectangle(source=OUTLINE, size=(50, 50))
            self._scroll_indicator_color = kv.Color(*self.indicator_color)
            self._scroll_indicator = kv.Rectangle()

    def _refresh_graphics(self, *args):
        self.canvas.clear()
        height = self.height
        item_height = self.item_height
        rect_count = max(1, int(height / item_height))
        size = self.width, item_height
        self._rects = []
        append = self._rects.append
        with self.canvas:
            for i in range(rect_count):
                pos = self._get_rect_pos(i)
                rect = kv.Rectangle(size=size, pos=pos, texture=EMPTY_TEXTURE)
                append(rect)
        self._refresh_items()
        self._refresh_selection_graphics()
        self._refresh_scroll_indicator()

    def _get_rect_pos(self, idx: int):
        x, y = self.to_window(*self.pos)
        return x, y + self.height - (self.item_height * (idx + 1))

    def _refresh_items(self, *args):
        items = self.items
        scroll = self.scroll
        item_count = len(items)
        for i, rect in enumerate(self._rects):
            text = None
            texture = EMPTY_TEXTURE
            idx = i + scroll
            if idx < item_count:
                text = items[idx]
                texture = self._get_texture(text)
            rect.texture = texture

    def _on_label_kwargs(self, w, kwargs):
        cache_remove("XList")
        self._refresh_graphics()

    def _refresh_label_kwargs(self, *args):
        self._label_kwargs = dict(
            font_name=self.font,
            font_size=self.font_size,
            text_size=(self.width, self.item_height),
            valign="middle",
        )

    def _get_texture(self, text: str):
        texture = cache_get("XList", text)
        if texture is None:
            label = kv.CoreMarkupLabel(text=text, **self._label_kwargs)
            label.refresh()
            texture = label.texture
            cache_append("XList", text, texture)
        return texture

    def _get_scroll(self):
        return self._scroll

    def _set_scroll(self, scroll):
        selection = self.selection
        line_count = len(self._rects)
        min_scroll = max(0, selection - line_count + 1)
        max_scroll = min(selection, len(self.items) - line_count)
        new_scroll = max(min_scroll, min(scroll, max_scroll))
        is_new_scroll = new_scroll != self._scroll
        self._scroll = new_scroll
        return is_new_scroll

    scroll = kv.AliasProperty(_get_scroll, _set_scroll)

    def invoke(self, *args, index: Optional[int] = None):
        if index is None:
            index = self.selection
        self.dispatch("on_invoked", index, self.items[index])

    def on_invoked(self, index: int, label: str):
        pass

    def keyboard_on_key_down(self, w, key_pair, text, mods):
        keycode, key = key_pair
        if key in {"up", "down", "pageup", "pagedown"}:
            self._handle_arrow_key(key, mods)
        elif key.isnumeric():
            try:
                index = int(key)
            except ValueError:
                index = None
            if index is not None:
                self.select(index)
                self.invoke()
        elif key in {"enter", "numpadenter"}:
            self.invoke()
        else:
            return super().keyboard_on_key_down(w, key_pair, text, mods)

    def _handle_arrow_key(self, key, mods):
        mods = set(mods) - {"numpad"}
        is_up = key.endswith("up")
        is_down = key.endswith("down")
        is_paging = key.startswith("page")
        is_ctrl = "ctrl" in mods
        is_shift = "shift" in mods
        item_count = len(self.items)
        paging_size = max(2, self.paging_size or int(len(self._rects) / 2))
        delta = item_count if is_ctrl else paging_size if is_paging else 1
        select = 0
        shift = 0
        if is_up:
            select = -delta
        elif is_down:
            select = delta
        if self.enable_shifting and is_shift:
            shift = select
        self.shift(delta=shift)
        self.select(delta=select)

    def shift(self, delta: int, index: Optional[int] = None):
        if delta == 0:
            return
        if index is None:
            index = self.selection
        items = list(self.items)
        moving = items.pop(index)
        new_index = index + delta
        new_index = max(0, min(new_index, len(items)))
        items.insert(new_index, moving)
        self.items = items

    def on_focus(self, w, focus):
        self._selection_rect_color.a = 0.5 + 0.5 * int(focus)
