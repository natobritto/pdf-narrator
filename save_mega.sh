#!/usr/bin/env bash
set -euo pipefail

# Usage: ./upload_mega.sh <file> [remote_folder]
# Example: ./upload_mega.sh song.mp3 /AudioUploads

FILE="${1:-}"
REMOTE_DIR="${2:-/AudioUploads}"

if [[ -z "$FILE" ]]; then
  echo "Usage: $0 <file> [remote_folder]"
  exit 2
fi

if [[ ! -f "$FILE" ]]; then
  echo "File not found: $FILE"
  exit 2
fi

# Ensure MEGAcmd is available
if ! command -v mega-put >/dev/null 2>&1; then
  echo "mega-put not found. Install MEGAcmd first."
  exit 1
fi

# Ensure we're logged in (mega-whoami exits non-zero if not)
if ! mega-whoami >/dev/null 2>&1; then
  echo "Not logged in. Run: mega-login your@email.com"
  exit 1
fi

# Ensure destination folder exists (ignore error if it already exists)
mega-mkdir -p "$REMOTE_DIR" >/dev/null 2>&1 || true

# Upload (overwrite if same name exists)
# -c = "create" (resume/continue) is useful for flaky connections on big files in some setups
mega-put "$FILE" "$REMOTE_DIR"

echo "Uploaded: $FILE -> $REMOTE_DIR/"
