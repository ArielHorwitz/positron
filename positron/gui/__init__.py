"""GUI package."""

from loguru import logger
from pathlib import Path
from . import kex as kx
from ..util import settings
from ..util.file import PROJ_DIR


# Fonts
BUILTIN_FONTS_DIR = PROJ_DIR / "positron" / "gui" / "fonts"

__default_font_styles = {
    # Code
    "code.regular": "firacode-light",
    "code.bold": "firacode-regular",
    "code.italic": "firacode-light",
    "code.bolditalic": "firacode-bold",
    # UI
    "ui.regular": "saucecodepro-regular",
    "ui.bold": "saucecodepro-bold",
    "ui.italic": "saucecodepro-italic",
    "ui.bolditalic": "saucecodepro-bolditalic",
}


def __get_font(category, style):
    font = settings.get(f"fonts.{category}.{style}")
    if font:
        font = str(Path(font).expanduser().resolve())
    else:
        ident = f"{category}.{style}"
        font = str(BUILTIN_FONTS_DIR / f"{__default_font_styles[ident]}.ttf")
    logger.debug(f"Registering font for {category=} {style=} {font=}")
    assert Path(font).is_file()
    return font


# Register fonts
for category in ["code", "ui"]:
    kw = {
        f"fn_{style}": __get_font(category, style)
        for style in ["regular", "bold", "italic", "bolditalic"]
    }
    kx.CoreLabel.register(category, **kw)


# Font kwargs for kivy properties
FONT_KW = dict(font_name="code", font_size=settings.get("fonts.code.size"))
UI_FONT_KW = dict(font_name="ui", font_size=settings.get("fonts.ui.size"))
# Font dimensions
CHAR_WIDTH, LINE_HEIGHT = kx.CoreMarkupLabel(**FONT_KW).get_extents(text=" ")
UI_CHAR_WIDTH, UI_LINE_HEIGHT = kx.CoreMarkupLabel(**UI_FONT_KW).get_extents(text=" ")
logger.debug(f"{CHAR_WIDTH=} {LINE_HEIGHT=}")
logger.debug(f"{UI_CHAR_WIDTH=} {UI_LINE_HEIGHT=}")
