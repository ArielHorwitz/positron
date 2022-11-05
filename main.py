"""Positron - Another Python IDE.

Usage: positron [options] [<path>]

Options:
  -h, --help          Show this help and quit
  -s, --settings <settings-file>
                      Use a custom settings files
  -l, --lint          Run the linter on the path and quit
  --debug-args        Debug argument parsing and quit
"""

from docopt import docopt
from pathlib import Path
from positron.util import settings


def _debug_args(args: dict):
    print("Parsed arguments:")
    for k, v in args.items():
        if len(k) > 17:
            print(f"  {k}\n      {v}")
        else:
            print(f"  {k:>20} :  {v}")


def _run_positron(project_path: Path):
    print("\n".join(["\n", "="*50, "Starting up Positron...", "="*50, "\n"]))

    # Late import since Kivy opens window on import
    from positron.analyze.session import Session
    from positron.gui.app import App
    from positron.gui.kex import restart_script

    app_session = Session(project_path)
    app = App(app_session)
    returncode = app.run()
    if returncode < 0:
        print("Restarting Positron...\n\n")
        restart_script()
    print("Quit Positron.")


def main():
    """Main script entry point."""
    args = docopt(options_first=True, more_magic=True)

    # Debug argument parsing
    if args.debug_args:
        _debug_args(args)
        quit()

    # Load custom settings
    if args["--settings"] is not None:
        settings.load([Path(args["--settings"])])

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


if __name__ == "__main__":
    main()
