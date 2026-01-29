#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./upload_mega.sh <file1> [file2 ...] [remote_folder]
# Examples:
#   ./upload_mega.sh song.mp3 song2.mp3
#   ./upload_mega.sh *.mp3 /AudioUploads

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 <file1> [file2 ...] [remote_folder]"
  exit 2
fi

# Default remote directory
REMOTE_DIR="/AudioUploads"

# If last argument starts with /, treat it as remote folder
if [[ "${!#}" == /* ]]; then
  REMOTE_DIR="${!#}"
  FILES=("${@:1:$#-1}")
else
  FILES=("$@")
fi

# Ensure MEGAcmd is available
if ! command -v mega-put >/dev/null 2>&1; then
  echo "mega-put not found. Install MEGAcmd first."
  exit 1
fi

# Ensure we're logged in
if ! mega-whoami >/dev/null 2>&1; then
  echo "Not logged in. Run: mega-login your@email.com"
  exit 1
fi

# Ensure destination folder exists
mega-mkdir -p "$REMOTE_DIR" >/dev/null 2>&1 || true

# Upload files
for FILE in "${FILES[@]}"; do
  if [[ ! -f "$FILE" ]]; then
    echo "Skipping (not a file): $FILE"
    continue
  fi

  echo "Uploading: $FILE → $REMOTE_DIR/"
  mega-put "$FILE" "$REMOTE_DIR"
done

echo "Upload complete."
