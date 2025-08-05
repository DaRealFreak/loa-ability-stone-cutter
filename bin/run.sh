#!/usr/bin/env bash

set -euo pipefail

# resolve script directory
# BASH_SOURCE[0] handles being sourced or called via symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$( readlink "$SOURCE" )"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# project root is the parent of bin/
ROOT_DIR="$( dirname "$SCRIPT_DIR" )"

# paths in project root
VENV_DIR="$ROOT_DIR/.venv"
REQ_FILE="$ROOT_DIR/requirements.txt"
MAIN_FILE="$ROOT_DIR/main.py"

# create venv if needed
if [ ! -d "$VENV_DIR" ]; then
  echo "creating virtual environment in $VENV_DIR..."
  python -m venv "$VENV_DIR"
fi

# activate
echo "activating virtual environment..."
source "$VENV_DIR/Scripts/activate"

# install deps
echo "installing requirements from $REQ_FILE..."
pip install -r "$REQ_FILE"

# run
echo "starting $MAIN_FILE..."
python "$MAIN_FILE"
