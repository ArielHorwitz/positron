# Welcome to Positron

Positron is an open source and public domain IDE for Python. Please note that Positron
is still in very early development, meaning it is not yet easy to learn how to use and
this help file is not very helpful for now until the program begins to stabilize.

This help file is generated every time you open Positron. If for any reason you wish to
restore this file to its original form, simply restart Positron.


## Getting started

Virtually everything possible in Positron is available via keyboard. Becoming familiar
with the hotkeys is important to feel comfortable with Positron. Hotkeys are denoted
with modifiers:
* `^` control
* `!` alt
* `+` shift
* `#` super/meta

Some hotkeys:
* Global
    * `^+ q`             quit Positron
    * `^+ w`             restart Positron
    * `f12`              explore config folder (see below for more details)
    * `f11`              open global settings file (see below for more details)
    * `f9`               explore project folder
    * `^ f5`             reload all files from disk
    * `^+ f5`            reload settings (some settings require restart)
    * `f1/f2/f3/f4`      focus panel 1 / 2 / 3 / 4
* Modals
    * `^ t`              project tree and file search
    * `^ k`              browse disk
    * `^ g`              goto line
    * `^ f`              find text
    * `^+ f`             search text in whole project
    * `^+ a`             code analysis
    * `^ e`              goto next error
    * `^+ e`             show all errors
* Code editor
    * `^ s`              save file to disk
    * `^+ delete`        delete file from disk
    * `f5`               reload file from disk
    * `^ up/down`        scroll up/down
    * `^+ up/down`       shift lines
    * `^+ d`             duplicate lines
    * `^ ]` / `^ [`      find next/previous
    * `^ \`              toggle comments
    * `^ u`              toggle upper/lower case
    * `^+ j`             join/split lines
    * `! enter/up/down`  use code completions


## Configuration and settings

The Positron configuration folder (shortened to `#/` by default) contains all of your
personal configuration files for Positron: settings, cached session data, logs, etc. You
can browse this folder using the command line argument (see `positron --help`), or via
hotkey (see above).

Browsing the default settings file (`#/settings/__defaults__.toml`) will give you some
idea of what can be done with positron. Settings are loaded from custom files first (as
provided from command line), then from `__global__` and then from the builtin defaults.
This allows you to modify settings globally, but also override them by combining custom
settings (see `positron --help`).


## Troubleshooting

If you are having problems starting up Positron, the best place to look would be the
errors log found in `#/logs/errors.log`. Usually it is a matter of misconfigured
settings, and a quick solution might be to [backup and] nuke your config folder.
