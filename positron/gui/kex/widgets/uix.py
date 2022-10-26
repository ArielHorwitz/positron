"""UI widgets."""
from typing import Optional, Any, Mapping
from itertools import chain
import re
from .. import kivy as kv
from ..util import (
    XWidget,
    ColorType,
    XColor,
)
from .layouts import (
    XBox,
    XAnchor,
)
from .input_manager import XInputManager


class XLabel(XWidget, kv.Label):
    """Label."""

    def __init__(self, fixed_width: bool = False, **kwargs):
        """Initialize the class.

        Args:
            fixed_width: Adjust the height of the label while maintaining width.
        """
        kwargs = {
            "markup": True,
            "halign": "center",
            "valign": "center",
        } | kwargs
        super().__init__(**kwargs)
        if fixed_width:
            self.bind(size=self._fix_height, text=self._fix_height)
        else:
            self.bind(size=self._on_size)

    def _fix_height(self, *a):
        self.text_size = self.size[0], None
        self.texture_update()
        self.set_size(hx=1, y=self.texture_size[1])

    def _on_size(self, *a):
        self.text_size = self.size


class XLabelClick(kv.ButtonBehavior, XLabel):
    """Label with ButtonBehavior."""

    pass


class XCheckBox(XWidget, kv.CheckBox):
    """CheckBox."""

    def toggle(self, *a):
        """Toggle the active state."""
        self.active = not self.active


class XCheckBoxText(XBox):
    """CheckBox with Label."""

    def __init__(self, text: str = ""):
        """Initialize the class.

        Args:
            text: Label text.
            kwargs: Keyword arguments for the Label.
        """
        super().__init__()
        self.checkbox = XCheckBox()
        self.label = XLabelClick(
            text=text,
            on_release=self.checkbox.toggle,
        )
        self.checkbox.set_size(y=30)
        checkbox_anchor = XAnchor.from_widget(self.checkbox)
        checkbox_anchor.set_size(x=30)
        self.add(self.label, checkbox_anchor)


class XButton(XWidget, kv.Button):
    """Button."""

    def __init__(
        self,
        background_color: ColorType = XColor.from_name("blue", 0.5).rgba,
        **kwargs,
    ):
        """Initialize the class.

        Args:
            background_color: Background color of the button.
        """
        kwargs = {
            "markup": True,
            "halign": "center",
            "valign": "center",
        } | kwargs
        super().__init__(**kwargs)
        self.background_color = background_color

    def on_touch_down(self, m):
        """Overrides base class method to only react to left clicks."""
        if m.button != "left":
            return False
        return super().on_touch_down(m)


class XToggleButton(kv.ToggleButtonBehavior, XButton):
    """ToggleButton."""

    active = kv.BooleanProperty(False)
    """Behaves like an alias for the `state` property being "down"."""

    def __init__(self, **kwargs):
        """Same arguments as kivy Button."""
        super().__init__(**kwargs)
        self.bind(state=self._set_active)
        self.bind(active=self._set_state)

    def toggle(self, *args):
        """Toggles the active state of the button."""
        self.active = not self.active

    def _set_state(self, *args):
        self.state = "down" if self.active else "normal"

    def _set_active(self, *args):
        self.active = self.state == "down"


class XImageButton(XWidget, kv.ButtonBehavior, kv.Image):
    """Image with ButtonBehavior mixin."""

    pass


class XEntryMixin:

    select_on_focus = kv.BooleanProperty(False)
    focus_brighter = kv.BooleanProperty(True)
    _background_color_focused = kv.ObjectProperty(None)
    _background_color_unfocused = kv.ObjectProperty(None)
    deselect_on_escape = kv.BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._focus_background_color(False)

    def _on_textinput_focused(self, w, focus):
        """Overrides base method to handle changing focus.

        Selects all text when focused, changes brightness, and
        fixes base class bugs relating to modifiers.
        """
        self._fix_textinput_modifiers()
        super()._on_textinput_focused(w, focus)
        self._focus_background_color(focus)
        if focus and self.select_on_focus:
            self.select_all()

    def _fix_textinput_modifiers(self):
        self._ctrl_l = False
        self._ctrl_r = False
        self._alt_l = False
        self._alt_r = False

    def _focus_background_color(self, focus):
        if not self.focus_brighter:
            return
        if self._background_color_focused is None:
            self._background_color_focused = self.background_color
        if self._background_color_unfocused is None:
            unfbg = XColor(*self._background_color_focused, v=0.5).rgba
            self._background_color_unfocused = unfbg
        if focus:
            self.background_color = self._background_color_focused
        else:
            self.background_color = self._background_color_unfocused

    def reset_cursor_selection(self, *a):
        """Resets the cursor position and selection."""
        self.cancel_selection()
        self.cursor = 0, 0
        self.scroll_x = 0
        self.scroll_y = 0

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        """Override base method to deselect instead of defocus on escape."""
        key, _ = keycode
        r = super().keyboard_on_key_down(window, keycode, text, modifiers)
        # Handle escape
        if key == 27:
            if not self.deselect_on_escape:
                self.cancel_selection()
                self.focus = True
        return r


class XEntry(XEntryMixin, XWidget, kv.TextInput):
    """TextInput with sane defaults."""

    def __init__(
        self,
        multiline: bool = False,
        background_color: list[float] = (0.2, 0.2, 0.2, 1),
        foreground_color: list[float] = (1, 1, 1, 1),
        text_validate_unfocus: bool = True,
        write_tab: bool = False,
        **kwargs,
    ):
        """Initialize the class.

        Args:
            multiline: If should allow multiple lines.
            background_color: Color of the background.
            foreground_color: Color of the foreground.
            text_validate_unfocus: If focus should be removed after validation
                (pressing enter on a single-line widget).
            kwargs: keyword arguments for TextInput.
        """
        super().__init__(
            background_color=background_color,
            foreground_color=foreground_color,
            multiline=multiline,
            text_validate_unfocus=text_validate_unfocus,
            write_tab=write_tab,
            **kwargs,
        )
        if not multiline:
            self.set_size(y=35)


class XCodeEntry(XEntryMixin, XWidget, kv.CodeInput):
    """CodeInput with modifications."""

    soft_tab = kv.BooleanProperty(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kv.Window.bind(focus=self._on_window_focus)
        self.cursor_width = "2sp"
        self.cursor_color = 1, 1, 0, 1

    def _on_window_focus(self, w, focus):
        self.cursor_blink = focus

    def visible_line_range(self):
        top_line = round(self.scroll_y / self.line_height)
        bot_line = top_line + round(self.height / self.line_height)
        return top_line, bot_line + 1

    def selected_line_range(self):
        if not self._selection:
            return self.cursor_row, self.cursor_row
        _, row_from = self.get_cursor_from_index(self._selection_from)
        _, row_to = self.get_cursor_from_index(self._selection_to)
        start, end = min(row_from, row_to), max(row_from, row_to)
        return start, end

    def insert_text(self, substring, *args, **kwargs):
        if substring == "\t" and self.soft_tab:
            substring = " " * self.tab_width
        super().insert_text(substring, *args, **kwargs)

    def duplicate(self):
        start, end = self.selected_line_range()
        line_count = end - start
        new_end = end + line_count
        lines = [""] + self._lines[start:end + 1]
        substring = "\n".join(lines)
        # Move cursor to end of last line
        self.cursor = len(self._lines[end]), end
        select_from = self.cursor_index() + 1
        # Paste
        self.insert_text(substring)
        select_to = self.cursor_index()
        # Select pasted lines
        self.select_text(select_from, select_to)

    def shift_lines(self, direction: int):
        self._shift_lines(direction)
        kv.Clock.schedule_once(lambda *a: self._shift_lines_custom(direction))

    def _shift_lines_custom(self, direction: int):
        # Custom `rows` init
        start, end = self.selected_line_range()
        if direction > 0:
            rows = (start, end), (end, end + 1)
        else:
            rows = (start, end), (start - 1, start)
        self._shift_lines(direction, rows=rows)

    def _shift_lines(
        self, direction, rows=None, old_cursor=None, from_undo=False
    ):
        if self._selection_callback:
            if from_undo:
                self._selection_callback.cancel()
            else:
                return

        lines = self._lines
        flags = list(reversed(self._lines_flags))
        labels = self._lines_labels
        rects = self._lines_rects
        orig_cursor = self.cursor
        sel = None
        if old_cursor is not None:
            self.cursor = old_cursor

        if not rows:
            sindex = self.selection_from
            eindex = self.selection_to
            if (sindex or eindex) and sindex != eindex:
                sindex, eindex = tuple(sorted((sindex, eindex)))
                sindex, eindex = self._expand_range(sindex, eindex)
            else:
                sindex, eindex = self._expand_range(self.cursor_index())
            srow = self.get_cursor_from_index(sindex)[1]
            erow = self.get_cursor_from_index(eindex)[1]
            sel = sindex, eindex

            if direction < 0 and srow > 0:
                psrow, perow = self._expand_rows(srow - 1)
                rows = ((srow, erow), (psrow, perow))
            elif direction > 0 and erow < len(lines) - 1:
                psrow, perow = self._expand_rows(erow)
                rows = ((srow, erow), (psrow, perow))

        else:
            (srow, erow), (psrow, perow) = rows
            if direction < 0:
                m1srow, m1erow = psrow, perow
                m2srow, m2erow = srow, erow
                cdiff = psrow - perow
                xdiff = srow - erow
            else:
                m1srow, m1erow = srow, erow
                m2srow, m2erow = psrow, perow
                cdiff = perow - psrow
                xdiff = erow - srow

            self._lines_flags = list(reversed(list(chain(
                flags[:m1srow],
                flags[m2srow:m2erow],
                flags[m1srow:m1erow],
                flags[m2erow:],
            ))))
            self._lines[:] = (
                lines[:m1srow]
                + lines[m2srow:m2erow]
                + lines[m1srow:m1erow]
                + lines[m2erow:]
            )
            self._lines_labels = (
                labels[:m1srow]
                + labels[m2srow:m2erow]
                + labels[m1srow:m1erow]
                + labels[m2erow:]
            )
            self._lines_rects = (
                rects[:m1srow]
                + rects[m2srow:m2erow]
                + rects[m1srow:m1erow]
                + rects[m2erow:]
            )
            self._trigger_update_graphics()
            csrow = srow + cdiff
            cerow = erow + cdiff
            sel = (
                self.cursor_index((0, csrow)),
                self.cursor_index((0, cerow))
            )
            self.cursor = self.cursor_col, self.cursor_row + cdiff

            if not from_undo:
                undo_rows = ((srow + cdiff, erow + cdiff),
                             (psrow - xdiff, perow - xdiff))
                self._undo.append({
                    'undo_command': ('shiftln', direction * -1, undo_rows,
                                     self.cursor),
                    'redo_command': ('shiftln', direction, rows, orig_cursor),
                })
                self._redo = []

        if sel:
            def cb(dt):
                self.select_text(*sel)
                self._selection_callback = None
            self._selection_callback = kv.Clock.schedule_once(cb)

    def find_next(
            self,
            text: str,
            move_cursor: bool = True,
    ) -> Optional[tuple[int, int]]:
        if not text:
            return None
        cursor = self.cursor_index()
        match = re.search(text, self.text[cursor:])
        wrap_offset = 0
        if match is None:
            wrap_offset = cursor
            match = re.search(text, self.text)
            if match is None:
                return None
        start, end = match.span()
        start, end = start + cursor - wrap_offset, end + cursor - wrap_offset
        if move_cursor:
            self.cursor = self.get_cursor_from_index(end)
            self.select_text(start, end)
        return start, end

    def find_prev(
        self,
        text: str,
        move_cursor: bool = True,
    ) -> Optional[tuple[int, int]]:
        if not text:
            return None
        cursor = self.cursor_index() - 1
        matches = list(re.finditer(text, self.text[:cursor]))
        if not matches:
            matches = list(re.finditer(text, self.text))
            if not matches:
                return None
        match = matches[-1]
        start, end = match.span()
        if move_cursor:
            self.cursor = self.get_cursor_from_index(end)
            self.select_text(start, end)
        return start, end


class XSlider(XWidget, kv.Slider):
    """Slider."""

    pass


class XSliderText(XBox):
    """Slider with Label."""

    def __init__(
        self,
        prefix: str = "",
        rounding: int = 3,
        box_kwargs: Optional[Mapping[str, Any]] = None,
        label_kwargs: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ):
        """Initialize the class.

        Args:
            prefix: Text to prefix the value presented in the label.
            rounding: How many decimal places to show.
            box_kwargs: Keyword arguments for XBox.
            label_kwargs: Keyword arguments for XLabel.
            kwargs: Keyword arguments for XSlider.
        """
        box_kwargs = {} if box_kwargs is None else box_kwargs
        label_kwargs = {} if label_kwargs is None else label_kwargs
        label_kwargs = {"halign": "left"} | label_kwargs
        slider_kwargs = {"cursor_size": (25, 25)} | kwargs
        super().__init__(**box_kwargs)
        self.rounding = rounding
        self.prefix = prefix
        self.label = XLabel(**label_kwargs)
        self.label.set_size(hx=0.2)
        self.slider = XSlider(**slider_kwargs)
        self.add(self.label)
        self.add(self.slider)
        self.slider.bind(value=self._set_text)
        self._set_text(self, self.slider.value)

    def _set_text(self, w, value):
        if isinstance(value, float):
            value = round(value, self.rounding)
        if value == round(value):
            value = int(value)
        self.label.text = str(f"{self.prefix}{value}")


class XSpinner(XWidget, kv.Spinner):
    """Spinner."""

    value = kv.StringProperty("")

    def __init__(self, update_main_text: bool = True, **kwargs):
        """Same keyword arguments for Spinner.

        Args:
            update_main_text: Update the button text based on the selected value.
        """
        super().__init__(**kwargs)
        self.update_main_text = update_main_text
        if update_main_text:
            self.text_autoupdate = True

    def on_select(self, data):
        """Overrides base method."""
        pass

    def _on_dropdown_select(self, instance, data, *largs):
        if self.update_main_text:
            self.text = data
        self.value = data
        self.is_open = False
        self.on_select(data)


class XDropDown(XWidget, kv.DropDown):
    """DropDown."""

    pass


class XPickColor(XBox):
    """Color picking widget."""

    color = kv.ObjectProperty(XColor(0.5, 0.5, 0.5, 1))

    def __init__(self, **kwargs):
        """Same keyword arguments for Slider."""
        super().__init__(orientation="vertical")
        self.set_size(x=300, y=100)
        update_color = self._update_from_sliders
        self.sliders = []
        for i, c in enumerate("RGBA"):
            slider_kwargs = {
                "range": (0, 1),
                "step": 0.01,
                "value_track": True,
                "value_track_color": XColor(**{c.lower(): 0.75}).rgba,
                "value_track_width": "6dp",
                "cursor_size": (0, 0),
            } | kwargs
            s = self.add(XSliderText(**slider_kwargs))
            s.slider.bind(value=update_color)
            self.sliders.append(s)
        self.r, self.g, self.b, self.a = self.sliders
        self.set_color(self.color)

    def set_color(self, color: XColor):
        """Set the current color."""
        self.r.slider.value = color.r
        self.g.slider.value = color.g
        self.b.slider.value = color.b
        self.a.slider.value = color.a

    def _update_from_sliders(self, *a):
        color = XColor(
            self.r.slider.value,
            self.g.slider.value,
            self.b.slider.value,
            self.a.slider.value,
        )
        is_bright = sum(color.rgb) > 1.5
        for s in self.sliders:
            s.label.color = (0, 0, 0, 1) if is_bright else (1, 1, 1, 1)
        self.make_bg(color)
        self.color = color


class XSelectColor(XLabelClick):
    """An XPickColor that drops down from an XLabelClick."""

    def __init__(
        self,
        prefix: str = "[u]Color:[/u]\n",
        show_color_values: bool = True,
        **kwargs,
    ):
        """Initialize the class.

        Args:
            prefix: Text to show before the RGB values.
            show_color_values: Show the RGB values of the current color.
            kwargs: Keyword arguments for the XLabelClick.
        """
        self.prefix = prefix
        self.show_color_values = show_color_values
        super().__init__(**kwargs)
        self.picker = XPickColor()
        self.dropdown = XDropDown(auto_width=False, on_dismiss=self._on_color)
        self.dropdown.set_size(*self.picker.size)
        self.dropdown.add(self.picker)
        self.picker.bind(size=lambda w, s: self.dropdown.set_size(*s))
        self.bind(on_release=self.dropdown.open)
        self.on_color()

    def _on_color(self, *args):
        color = self.picker.color
        self.make_bg(color)
        text = self.prefix
        if self.show_color_values:
            text += " , ".join(str(round(c, 2)) for c in color.rgba)
        self.text = text


class XScreen(XWidget, kv.Screen):
    """Screen that can only contain one widget."""

    def __init__(self, **kwargs):
        """Same arguments as Screen."""
        super().__init__(**kwargs)
        self.view = None

    def add(self, *args, **kwargs) -> XWidget:
        """Overrides base method to set the view."""
        self.view = super().add(*args, **kwargs)
        if len(self.children) > 1:
            raise RuntimeError(
                f"Cannot add more than 1 widget to XScreen: {self.children=}"
            )


class XScreenManager(XWidget, kv.ScreenManager):
    """ScreenManager with custom transition behavior."""

    transition_speed = kv.NumericProperty(0.4)

    def __init__(self, **kwargs):
        """Same arguments as for ScreenManager, minus transition."""
        if "transition" in kwargs:
            del kwargs["transition"]
        super().__init__(**kwargs)
        self.transition = kv.SlideTransition(
            direction="left",
            duration=self.transition_speed,
        )

    def add_screen(self, name: str, widget: XWidget) -> XScreen:
        """Add a screen."""
        screen = self.add(XScreen(name=name))
        screen.add(widget)
        return screen

    def switch_name(self, name: str) -> bool:
        """Switch to a screen by name."""
        if name == self.current:
            return True
        if self.mid_transition:
            return False
        if name not in self.screen_names:
            raise ValueError(f'Found no screen by name "{name}" in {self.screen_names}')
        old_index = self.screen_names.index(self.current)
        new_index = self.screen_names.index(name)
        dir = "left" if old_index < new_index else "right"
        self.transition = kv.SlideTransition(
            direction=dir,
            duration=self.transition_speed,
        )
        self.current = name
        return True

    @property
    def mid_transition(self) -> bool:
        """If there is a transition in progress."""
        return 0 < self.current_screen.transition_progress < 1

    @classmethod
    def from_widgets(cls, widgets: Mapping[str, XWidget], **kwargs) -> "XScreenManager":
        """Create an XScreenManager from a dictionary of screen names and widgets."""
        sm = cls(**kwargs)
        for n, w in widgets.items():
            screen = XScreen(name=n)
            screen.add(w)
            sm.add(screen)
        return sm


class XModalView(XWidget, kv.ModalView):
    pass


class XModal(XAnchor):
    """A XAnchor with an XInputManager that can de/attach to a container."""

    def __init__(self, container: XAnchor, name: str = "Unnamed", **kwargs):
        super().__init__(**kwargs)
        self.container = container
        self.im = XInputManager(name=name, active=False)
        self.im.register("Dismiss", self.dismiss, "escape")
        self.bind(parent=self._on_parent)

    def toggle(self, *args, set_as: Optional[bool] = None):
        if set_as is None:
            set_as = self.parent is None
        if set_as:
            self.open()
        else:
            self.dismiss()

    def open(self, *args):
        if self.parent is not None:
            return
        self.container.add_widget(self)

    def dismiss(self, *args):
        if self.parent is None:
            return
        self.container.remove_widget(self)

    def _on_parent(self, w, parent):
        self.im.active = parent is not None
