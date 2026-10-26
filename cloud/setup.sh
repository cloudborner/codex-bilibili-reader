#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
if command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
else
  python3 -m venv .cloud-bootstrap
  .cloud-bootstrap/bin/python -m pip install 'uv==0.13.5'
  UV="$PWD/.cloud-bootstrap/bin/uv"
fi
"$UV" sync --frozen --no-dev --python "$(command -v python3)"
.venv/bin/python -m bili_cli.cli --version
.venv/bin/python -m bili_cli.cli search --help >/dev/null
printf '%s\n' 'Dependencies ready. Cloud network and Bilibili login are separate checks.'
