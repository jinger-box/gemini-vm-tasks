#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/workspace/state" "$HOME/workspace/logs" "$HOME/.secrets"
chmod 700 "$HOME/.secrets"

if ! python3 -c "import yaml" 2>/dev/null; then
  echo "PyYAML の導入を試みます（失敗しても標準ライブラリのみで動作します）..."
  python3 -m pip install --user --quiet pyyaml 2>/dev/null || true
fi

chmod +x "$(dirname "$0")/scripts/watch_github.py"

echo "セットアップ完了:"
echo "  state:   $HOME/workspace/state"
echo "  logs:    $HOME/workspace/logs"
echo "  secrets: $HOME/.secrets (mode 700)"
echo "動作確認: python3 $(cd "$(dirname "$0")" && pwd)/scripts/watch_github.py"
