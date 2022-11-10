# flake8: noqa
# Ignoring flake8 errors E402,F401 because of late imports and unused imports
"""The Kex library.

An interface to the [Kivy](https://kivy.org/) library with extended widgets for
convenience. It focuses on making it easier (and maybe a little more intuitive)
to write kivy apps programmatically.

## KexMixin
The `KexMixin` class is a mixin class for kivy widgets with convenience methods.
"""
import os as __os

# Kivy configuration must be done before importing kivy
__os.environ["KIVY_NO_ARGS"] = "1"  # no consuming script arguments
__os.environ["KCFG_KIVY_LOG_LEVEL"] = "warning"  # no spamming console on startup


from .kivy import (
    ButtonBehavior,
    FocusBehavior,
    ToggleButtonBehavior,
    NoTransition,
    FadeTransition,
    CardTransition,
    SlideTransition,
    SwapTransition,
    WipeTransition,
    ShaderTransition,
    InstructionGroup,
    Color,
    Rectangle,
    Rotate,
    PushMatrix,
    PopMatrix,
    ObjectProperty,
    AliasProperty,
    StringProperty,
    NumericProperty,
    BooleanProperty,
    ListProperty,
    DictProperty,
    OptionProperty,
    ReferenceListProperty,
    CoreLabel,
    CoreMarkupLabel,
)
from .util import (
    XWindow as Window,
    XColor,
    get_color,
    random_color,
    center_sprite,
    text_texture,
    restart_script,
    placeholder,
    consume_args,
    schedule_once,
    schedule_interval,
    create_trigger,
    snoozing_trigger,
    queue_around_frame,
)
from .widgets import XBaseWidget as Widget
from .widgets.layouts import (
    XBox as Box,
    XZBox as ZBox,
    XDBox as DBox,
    XGrid as Grid,
    XRelative as Relative,
    XStack as Stack,
    XAnchor as Anchor,
    XScroll as Scroll,
)
from .widgets.uix import (
    XLabel as Label,
    XCheckBox as CheckBox,
    XCheckBoxText as CheckBoxText,
    XButton as Button,
    XToggleButton as ToggleButton,
    XImageButton as ImageButton,
    XEntry as Entry,
    XCodeEntry as CodeEntry,
    XSlider as Slider,
    XSliderText as SliderText,
    XSpinner as Spinner,
    XDropDown as DropDown,
    XPickColor as PickColor,
    XSelectColor as SelectColor,
    XScreenManager as ScreenManager,
    XScreen as Screen,
    XModalView as ModalView,
    XModal as Modal,
)
from .widgets.input_manager import XInputManager as InputManager
from .widgets.app import XApp as App


__all__ = []
