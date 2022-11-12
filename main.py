"""Positron - Another Python IDE.

Usage: positron [options] [<path>]

Options:
  -h, --help          Show this help and quit
  -s, --settings <settings-file>
                      Use a custom settings files
  -l, --lint          Run the linter on the path and quit
  --debug-args        Debug argument parsing and quit
"""

from loguru import logger
import sys
from docopt import docopt
from pathlib import Path
from positron.util import settings


logger.add(settings.USER_DIR / "debug.log", level="DEBUG", rotation="1 MB")
logger.add(settings.USER_DIR / "errors.log", level="WARNING", rotation="100 KB")


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
    if args["--settings"] is not None:
        custom_settings = Path(args["--settings"])
        if custom_settings.is_file():
            settings.load([custom_settings])
        else:
            logger.warning(f"Custom settings file does not exist: {custom_settings}")

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
