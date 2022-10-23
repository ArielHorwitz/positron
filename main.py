"""Another IDE for python (prototype)."""


def run():
    """Main script entry point."""

    print("\n".join(["\n", "="*50, "Starting up NIDE...", "="*50, "\n"]))

    import sys
    from pathlib import Path
    from nide.gui.app import App
    from nide.gui.kex import restart_script
    from nide.util.session import Session

    project_path = Path.cwd()
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    app_session = Session(project_path)
    app = App(app_session)
    returncode = app.run()
    if returncode < 0:
        print("Restarting NIDE...\n\n")
        restart_script()
    print("Quit NIDE.")


if __name__ == "__main__":
    run()
