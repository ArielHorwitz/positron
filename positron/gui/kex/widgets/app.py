"""App and associated widgets.

Generally, to use the GUI, one would initialize and then run an `App`:
```python
app = XApp()
app.hook(func_to_call_every_frame, fps=20)
app.run()
```
"""
from typing import Callable, Optional
from functools import partial
from .. import kivy as kv
from ..util import (
    XColor,
    XWindow,
    XWidget,
    consume_args,
    SimpleCallable,
    queue_around_frame,
)
from .layouts import XAnchor
from .uix import XLabel
from .win_focus_patch import WindowFocusPatch


class XOverlay(kv.FocusBehavior, XAnchor):
    """Overlay to be displayed on top of other widgets."""

    def __init__(self, **kwargs):
        """Initialize like an XAnchor."""
        super().__init__()
        self.make_bg(XColor(a=0.5))
        self.label = self.add(XLabel(**kwargs))
        self.label.set_size(x=500, y=150)
        self.label.make_bg(XColor.from_name("red", 0.15))


class XRoot(kv.FocusBehavior, XAnchor):
    """Root widget for the app, with FocusBehavior."""

    pass


class XApp(XWidget, kv.App):
    """See module documentation for details."""

    current_focus = kv.ObjectProperty(None)
    """Currently focused widget."""
    block_input = kv.BooleanProperty(False)
    """If all user input should be blocked."""

    def __init__(self, escape_exits: bool = False, **kwargs):
        """Initialize the class."""
        self.__window_focus_path = WindowFocusPatch()
        super().__init__(**kwargs)
        XWindow.enable_escape_exit(escape_exits)
        self.root = XRoot()
        self.keyboard = kv.Window.request_keyboard(consume_args, self.root)
        self.__restart_flag = False
        self.__last_focused = None
        self.__overlay = None
        XWindow.disable_multitouch()
        kv.Clock.schedule_interval(self._check_focus, 1 / 60)
        kv.Window.bind(
            on_touch_down=self._filter_touch,
            on_touch_up=self._filter_touch,
            on_touch_move=self._filter_touch,
        )

    def _check_focus(self, dt):
        self.current_focus = self.keyboard.target

    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)
        return -1 if self.__restart_flag else 0

    def restart(self, *args):
        self.__restart_flag = True
        self.stop()

    def hook(self, func: Callable[[float], None], fps: float):
        """Schedule *func* to be called *fps* times per seconds."""
        kv.Clock.schedule_once(
            lambda *a: kv.Clock.schedule_interval(func, 1 / fps),
            0,
        )

    def open_settings(self, *args) -> False:
        """Overrides base class method to disable the builtin settings widget."""
        return False

    @property
    def mouse_pos(self) -> tuple[float, float]:
        """The current position of the mouse."""
        return XWindow.mouse_pos

    def add(self, *args, **kwargs):
        """Add a widget to the root widget."""
        return self.root.add(*args, **kwargs)

    @property
    def overlay(self) -> Optional[XOverlay]:
        """The current overlay."""
        return self.__overlay

    def _filter_touch(self, w, touch):
        if self.block_input:
            return True
        if "button" not in touch.profile:
            return True
        return False

    def __create_overlay(self, **kwargs):
        self.__last_focused = self.current_focus
        self.__overlay = XOverlay(**kwargs)
        self.__overlay.focus = True
        self.block_input = True
        self.add(self.__overlay)

    def __destroy_overlay(self, after: Optional[SimpleCallable] = None):
        if self.__last_focused is not None:
            self.__last_focused.focus = True
        self.root.remove_widget(self.__overlay)
        self.__overlay = None
        self.block_input = False
        if after is not None:
            after()

    def with_overlay(
        self,
        func: SimpleCallable,
        after: Optional[SimpleCallable] = None,
        **kwargs,
    ):
        """Queue a function with a temporary `XOverlay` that blocks input.

        Uses the `botroyale.gui.kex.util.queue_around_frame` decorator to draw
        a frame before calling the function, otherwise the added overlay will
        not be seen until execution is yielded to kivy's clock.

        Example usage:
        ```python
        with_overlay(
            func=lambda: my_func(arg1=True),
            text="my_func is executing...",
            after=lambda: print("finished executing my_func."),
        )
        ```

        Args:
            func: Callback to queue after adding the overlay.
            after: Optionally call after removing the overlay.
            kwargs: Keyword arguments for the XOverlay object.
        """
        if self.__overlay is not None:
            raise RuntimeError("Cannot create an overlay when one already exists.")
        queue_around_frame(
            func,
            before=partial(self.__create_overlay, **kwargs),
            after=partial(self.__destroy_overlay, after),
        )()
