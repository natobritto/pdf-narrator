#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <file>.wav" >&2
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

INPUT_PATH="$1"

if [[ ! -f "$INPUT_PATH" ]]; then
  echo "Error: file not found: $INPUT_PATH" >&2
  exit 1
fi

if [[ "$INPUT_PATH" != *.wav ]]; then
  echo "Error: input must be a .wav file: $INPUT_PATH" >&2
  exit 1
fi

# Load Google Drive upload settings from gdrive_config.json if env vars not set
if [[ -z "${GDRIVE_REMOTE:-}" || -z "${GDRIVE_FOLDER:-}" ]]; then
  GDRIVE_REMOTE="${GDRIVE_REMOTE:-$(python - <<'PY'
import json, os
path = os.path.join(os.getcwd(), "gdrive_config.json")
if not os.path.exists(path):
    print("")
    raise SystemExit
try:
    cfg = json.load(open(path, "r", encoding="utf-8")) or {}
    print(cfg.get("remote", ""))
except Exception:
    print("")
PY
)}"
  GDRIVE_FOLDER="${GDRIVE_FOLDER:-$(python - <<'PY'
import json, os
path = os.path.join(os.getcwd(), "gdrive_config.json")
if not os.path.exists(path):
    print("")
    raise SystemExit
try:
    cfg = json.load(open(path, "r", encoding="utf-8")) or {}
    print(cfg.get("folder", ""))
except Exception:
    print("")
PY
)}"
fi

if [[ -z "${GDRIVE_REMOTE:-}" || -z "${GDRIVE_FOLDER:-}" ]]; then
  echo "Error: missing GDRIVE_REMOTE or GDRIVE_FOLDER (env or gdrive_config.json)." >&2
  exit 1
fi

if command -v rclone >/dev/null 2>&1; then
  rclone copy "$INPUT_PATH" "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}" >/dev/null 2>&1 || true
  echo "Uploaded: $INPUT_PATH -> ${GDRIVE_REMOTE}:${GDRIVE_FOLDER}"
else
  echo "Warning: rclone not found; skipping Google Drive upload." >&2
  exit 1
fi
