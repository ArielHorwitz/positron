"""Another IDE for python (prototype)."""


def run():
    """Main script entry point."""

    print("\n".join(["\n", "="*50, "Starting up Positron...", "="*50, "\n"]))

    import sys
    from pathlib import Path
    from positron.util.file import PROJ_DIR
    from positron.util import settings
    from positron.analyze.session import Session
    from positron.gui.app import App
    from positron.gui.kex import restart_script

    if len(sys.argv) <= 1:
        # Default session
        project_path = Path(settings.get("project.default")).expanduser().resolve()
    else:
        # Session from command args
        project_path = Path(sys.argv[1]).expanduser().resolve()
    app_session = Session(project_path)
    app = App(app_session)
    returncode = app.run()
    if returncode < 0:
        print("Restarting Positron...\n\n")
        restart_script()
    print("Quit Positron.")


if __name__ == "__main__":
    run()
