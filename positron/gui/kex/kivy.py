"""Module for collecting common Kivy imports from various subpackages."""
# flake8: noqa
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.cache import Cache
from kivy.core.text import Label as CoreLabel
from kivy.core.text.markup import MarkupLabel as CoreMarkupLabel
from kivy.core.window import Window, Keyboard
from kivy.utils import escape_markup
from kivy.properties import (
    ObjectProperty,
    AliasProperty,
    StringProperty,
    NumericProperty,
    BooleanProperty,
    ListProperty,
    DictProperty,
    OptionProperty,
    ColorProperty,
    ReferenceListProperty,
)

# Widgets
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.dropdown import DropDown
from kivy.uix.slider import Slider
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.codeinput import CodeInput
from kivy.uix.image import Image

# Mixins
from kivy.uix.behaviors import (
    ButtonBehavior,
    FocusBehavior,
    ToggleButtonBehavior,
)

# Animation
from kivy.uix.screenmanager import (
    ScreenManager,
    Screen,
    NoTransition,
    FadeTransition,
    CardTransition,
    SlideTransition,
    SwapTransition,
    WipeTransition,
    ShaderTransition,
)

# Graphics
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import (
    Color,
    Rectangle,
    Rotate,
    PushMatrix,
    PopMatrix,
)

# Audio
from kivy.core.audio import SoundLoader
