# Welcome to Positron

Positron is an open source and public domain IDE for Python. Please note that Positron
is still in very early development, meaning it is not yet easy to learn how to use and
this help file is not very helpful for now until the program begins to stabilize.

This help file is generated every time you open Positron. If for any reason you wish to
restore this file to its original form, simply restart Positron.


## Configuration and settings

The Positron configuration folder (shortened to `#/` by default) contains all of your
personal configuration files for Positron: settings, cached session data, logs, etc. To
open the configuration folder, use the hotkey `f12`.

Browsing the default settings file (`#/settings/__defaults__.toml`) will give you some
idea of what can be done with positron. Settings are loaded from custom files first (as
provided from command line), then from `__global__` and then from the builtin defaults.
This allows you to modify settings globally, but also override them by combining custom
settings (see `run-positron.sh --help` in command line).


## Getting started

Virtually everything available in Positron is available via keyboard. Becoming familiar
with the hotkeys is important to feel comfortable with Positron. Currently, the only way
to see the hotkeys available is via debugging using `ctrl + alt + shift + pause` and
browsing debug log at `#/logs/debug.log`.


## Troubleshooting

If you are having problems starting up Positron, the best place to look would be the
errors log found in `#/logs/errors.log`. Usually it is a matter of misconfigured
settings, and a quick solution might be to [backup and] nuke your config folder.
