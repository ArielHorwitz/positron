"""Another IDE for python (prototype)."""

import sys
from pathlib import Path
from nide.gui.app import App
from nide.session import Session


PROJ_PATH = Path.cwd()


def run():
    """Main script entry point."""
    project_path = PROJ_PATH
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    app_session = Session(project_path)
    app = App(app_session)
    app.run()


if __name__ == "__main__":
    run()
