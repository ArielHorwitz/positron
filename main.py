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
from docopt import docopt
from pathlib import Path
from positron.util.file import LOGS_DIR
from positron.util import settings


logger.add(LOGS_DIR / "debug.log", level="DEBUG", rotation="1 MB")
logger.add(LOGS_DIR / "errors.log", level="WARNING", rotation="100 KB")


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
    logger.info("\n".join(["\n", "="*50, "Starting up Positron...", "="*50, "\n"]))

    # Late import since Kivy opens window on import
    from positron.analyze.session import Session
    from positron.gui.app import App
    from positron.gui.kex import restart_script

    app_session = Session(project_path)
    app = App(app_session)
    returncode = app.run()
    if returncode < 0:
        logger.info("Restarting Positron...\n\n")
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
