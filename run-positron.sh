#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_DIR"/venv/bin/activate"
echo "POSITRON VENV:" $VIRTUAL_ENV

python3 $SCRIPT_DIR"/main.py" $@
