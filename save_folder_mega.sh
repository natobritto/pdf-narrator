#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./save_folder_mega.sh <local_folder> [remote_folder]
#
# Examples:
#   ./save_folder_mega.sh "deep researches"
#   ./save_folder_mega.sh "deep researches" /AudioUploads

LOCAL_DIR="${1:-}"
REMOTE_DIR="${2:-}"

if [[ -z "$LOCAL_DIR" ]]; then
  echo "Usage: $0 <local_folder> [remote_folder]"
  exit 2
fi

if [[ ! -d "$LOCAL_DIR" ]]; then
  echo "Folder not found: $LOCAL_DIR"
  exit 2
fi

# Build command safely
if [[ -n "$REMOTE_DIR" ]]; then
  find "$LOCAL_DIR" -name "*.wav" -print0 \
    | xargs -0 ./save_mega.sh "$REMOTE_DIR"
else
  find "$LOCAL_DIR" -name "*.wav" -print0 \
    | xargs -0 ./save_mega.sh
fi

# find $1 -name "*.wav" -print0 | xargs -0 ./save_mega.sh
# find "deep researches/" -name "*.wav" -print0 | xargs -0 du -ch
