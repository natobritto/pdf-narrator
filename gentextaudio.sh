#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [--say] \"text to speak\" [output.wav] [voicepack]" >&2
  echo "Example: $0 \"Hello world\" --say hello.wav am_liam" >&2
}

SAY_AUDIO=0
POSITIONAL=()
for arg in "$@"; do
  if [[ "$arg" == "--say" ]]; then
    SAY_AUDIO=1
  else
    POSITIONAL+=("$arg")
  fi
done
set -- "${POSITIONAL[@]}"

if [[ $# -lt 1 || $# -gt 3 ]]; then
  usage
  exit 1
fi

TEXT_INPUT="$1"
OUTPUT_PATH="${2:-tts_output.wav}"
VOICE_OVERRIDE="${3:-}"

# Resolve script directory to find sibling scripts reliably
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# If first arg is a PDF path, route to genpdfaudio.sh
if [[ -f "$TEXT_INPUT" && "$TEXT_INPUT" == *.pdf ]]; then
  if [[ -n "${2:-}" ]]; then
    echo "Note: output filename is ignored for PDF input; using genpdfaudio.sh defaults." >&2
  fi
  if [[ ! -x "$SCRIPT_DIR/genpdfaudio.sh" ]]; then
    echo "Error: genpdfaudio.sh not found or not executable at: $SCRIPT_DIR/genpdfaudio.sh" >&2
    exit 1
  fi
  "$SCRIPT_DIR/genpdfaudio.sh" "$TEXT_INPUT" "$VOICE_OVERRIDE"
  exit 0
fi

python - "$TEXT_INPUT" "$OUTPUT_PATH" "$VOICE_OVERRIDE" <<'PY'
import json
import os
import sys
import tempfile

from generate_audiobook_kokoro import generate_audio_for_file_kokoro
from kokoro import KPipeline

text = sys.argv[1]
output_path = os.path.abspath(sys.argv[2])
voice_override = sys.argv[3] if len(sys.argv) > 3 else ""

cfg = {}
config_path = os.path.join(os.getcwd(), "config.json")
if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
    except Exception as e:
        print(f"Warning: failed to read config.json: {e}")

audio_cfg = cfg.get("audio_settings", {}) or {}

voice = voice_override or audio_cfg.get("voicepack") or "am_liam"
device = audio_cfg.get("device", "cpu")

print(f"Output        : {output_path}")
print(f"Voice / Lang  : {voice} / {voice[0]}")
print(f"Device        : {device}")

with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".txt") as tf:
    tf.write(text)
    temp_path = tf.name

try:
    pipeline = KPipeline(lang_code=voice[0], device=device, repo_id='hexgrad/Kokoro-82M')
    ok = generate_audio_for_file_kokoro(
        input_path=temp_path,
        pipeline=pipeline,
        voice=voice,
        output_path=output_path,
    )
    if not ok:
        raise RuntimeError("Audio generation failed")
finally:
    try:
        os.unlink(temp_path)
    except Exception:
        pass

print(f"Saved WAV: {output_path}")
PY

if [[ "$SAY_AUDIO" -eq 1 ]]; then
  paplay "$OUTPUT_PATH"
fi
