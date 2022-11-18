# Positron

Positron is an IDE for Python written in Python using Positron.

Developed as a hobby project for personal use and released to the public domain.
Positron relies heavily on
[Kivy](https://kivy.org/),
[jedi](https://github.com/davidhalter/jedi),
[flake8](https://github.com/pycqa/flake8),
and more. A massive shoutout to these projects!


## Features

The following features are currently supported:
* Linux-only
* Highly customizable
* Syntax highlighting
* Auto completion
* Code analysis
* Static error checking (linting)
* Snippets (automatic text insertion)
* Project folder indexing (tree view and fuzzy search)
* Disk browsing and bookmarks
* Find text
* Goto line


## Installation
```
git clone git@github.com:ArielHorwitz/positron.git  # Clone the repo
cd positron                                         # Move into the new folder
python -m venv venv                                 # Create a virtual environment
source venv/bin/activate                            # Activate virtual environment
pip install --upgrade pip                           # Update pip
pip install -r requirements.txt                     # Install all requirements
```

## Run
```
/path/to/positron/run-positron.sh /path/to/file/or/folder
```
