"""GUI package."""

from loguru import logger
from . import kex as kx
from ..util import settings
from ..util.file import PROJ_DIR


# Fonts
FONTS_DIR = PROJ_DIR / "positron" / "gui" / "fonts"
FONT = str(FONTS_DIR / settings.get("editor.font"))
FONT_SIZE = settings.get("editor.font_size")
UI_FONT = str(FONTS_DIR / settings.get("ui.font"))
UI_FONT_SIZE = settings.get("ui.font_size")

# Font details
FONT_KW = dict(font_name=FONT, font_size=FONT_SIZE)
UI_FONT_KW = dict(font_name=UI_FONT, font_size=UI_FONT_SIZE)

# Font dimensions
CHAR_WIDTH, LINE_HEIGHT = kx.CoreMarkupLabel(
    font_name=FONT, font_size=FONT_SIZE,
).get_extents(text=" ")
UI_CHAR_WIDTH, UI_LINE_HEIGHT = kx.CoreMarkupLabel(
    font_name=UI_FONT, font_size=UI_FONT_SIZE,
).get_extents(text=" ")

# Font debugging
logger.debug(f"{CHAR_WIDTH=} {LINE_HEIGHT=}")
logger.debug(f"{UI_CHAR_WIDTH=} {UI_LINE_HEIGHT=}")
