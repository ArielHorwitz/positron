"""Positron - Another Python IDE.

Usage: positron [options] [<path>]

Options:
  -h, --help          Show this help and quit
  -s, --settings <settings-names>
                      Use custom settings with comma-separated names
  -l, --lint          Run the linter on the path and quit
  --debug-args        Debug argument parsing and quit


Custom settings:
    Settings names can be full file paths, or the "{name}" part of
        "$SETTINGS_DIR/settings-{name}.toml".

    For example, "mini,dev,custom/settings/file.toml" will load the files
        - "$SETTINGS_DIR/settings-mini.toml"
        - "$SETTINGS_DIR/settings-dev.toml"
        - "custom/settings/file.toml"
"""

from loguru import logger
import sys
import random
from docopt import docopt
from pathlib import Path
from positron.util.file import LOGS_DIR
from positron.util import settings


# Configure logging
SESSION_ID = f"{random.randint(0, 10**8):x}"
LOG_FORMAT = (
    f"<red>{SESSION_ID}</red> | "
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:^8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
logger.add(
    LOGS_DIR / "debug.log",
    level="DEBUG",
    format=LOG_FORMAT,
    rotation="500 KB",
    retention=1,
)
logger.add(
    LOGS_DIR / "errors.log",
    level="WARNING",
    format=LOG_FORMAT,
    rotation="500 KB",
    retention=1,
)
logger.info(f"Session ID: {SESSION_ID}")


@logger.catch
def main():
    """Main script entry point."""
    logger.debug(f"{sys.argv=}")
    args = docopt(options_first=True, more_magic=True)

    # Debug argument parsing
    if args.debug_args:
        _debug_args(args)
        quit()

    # Load custom settings
    custom_settings = args["--settings"] or []
    if custom_settings:
        custom_settings = custom_settings.split(",")
    settings.load(custom_settings)

    # Find the path to open
    if args.path:
        project_path = Path(args.path)
    else:
        project_path = Path(settings.get("project.default")).expanduser().resolve()

    # Lint
    if args.lint:
        from positron.analyze.linter import lint_path
        lint_path(project_path, capture_output=False)
        quit()

    # Run app
    _run_positron(project_path)


def _run_positron(project_path: Path):
    logger.info("Starting up Positron...")

    # Late import since Kivy opens window on import
    from positron.gui.app import App
    from positron.gui.kex import restart_script

    app = App(project_path)
    returncode = app.run()
    unused_settings = settings.unused()
    if unused_settings:
        logger.warning(f"Unused settings: {unused_settings}")
    if returncode < 0:
        logger.info("Restarting Positron...\n")
        restart_script()
    logger.info("Quit Positron.")


def _debug_args(args: dict):
    logger.info("Parsed arguments:")
    for k, v in args.items():
        if len(k) > 17:
            logger.info(f"  {k}\n      {v}")
        else:
            logger.info(f"  {k:>20} :  {v}")


if __name__ == "__main__":
    main()
