#!/usr/bin/env bash
# Install typer-test as a command on your PATH.
#   ./install.sh            -> installs to ~/.local/bin/typer-test
#   ./install.sh /usr/local/bin   -> installs elsewhere (may need sudo)
set -euo pipefail

DEST="${1:-$HOME/.local/bin}"
SRC="$(cd "$(dirname "$0")" && pwd)/typer_test.py"

mkdir -p "$DEST"
install -m 755 "$SRC" "$DEST/typer-test"
echo "Installed: $DEST/typer-test"

case ":$PATH:" in
    *":$DEST:"*) ;;
    *)
        echo
        echo "Note: $DEST is not on your PATH. Add this to your ~/.bashrc:"
        echo '  export PATH="$HOME/.local/bin:$PATH"'
        ;;
esac

echo
echo "Done. Start it with:  typer-test"
