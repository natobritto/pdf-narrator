#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <file>.pdf|<folder> [voicepack]" >&2
  echo "Example: $0 ./book.pdf am_liam" >&2
  echo "Example: $0 ./pdfs/ am_liam" >&2
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

INPUT_PATH="$1"
VOICE_OVERRIDE="${2:-}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

process_pdf() {
  local pdf_path="$1"
  local base_name
  local final_output
  base_name="$(basename "${pdf_path%.*}")"
  final_output="$(dirname "$pdf_path")/${base_name}.wav"

  if [[ -s "$final_output" ]]; then
    echo "Skipping (cached): $pdf_path -> $final_output"
  else
    python - "$pdf_path" "$VOICE_OVERRIDE" <<'PY'
import json
import os
import sys

import numpy as np
import soundfile as sf

from extract import extract_book
from generate_audiobook_kokoro import generate_audiobooks_kokoro

input_path = os.path.abspath(sys.argv[1])
voice_override = sys.argv[2] if len(sys.argv) > 2 else ""

cfg = {}
config_path = os.path.join(os.getcwd(), "config.json")
if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
    except Exception as e:
        print(f"Warning: failed to read config.json: {e}")

source_cfg = cfg.get("source_settings", {}) or {}
audio_cfg = cfg.get("audio_settings", {}) or {}

use_toc = bool(source_cfg.get("use_toc", True))
extract_mode = source_cfg.get("extract_mode", "chapters")

voice = voice_override or audio_cfg.get("voicepack") or "am_liam"
audio_format = ".wav"
device = audio_cfg.get("device", "cpu")

base_name = os.path.splitext(os.path.basename(input_path))[0]
extracted_dir = os.path.join(os.getcwd(), "extracted_books", base_name)
audio_dir = os.path.join(os.getcwd(), "audiobooks", base_name)
final_output = os.path.join(os.path.dirname(input_path), f"{base_name}.wav")

print(f"Input           : {input_path}")
print(f"Extracted text  : {extracted_dir}")
print(f"Audio output    : {audio_dir}")
print(f"Final output    : {final_output}")
print(f"Voice / Lang    : {voice} / {voice[0]}")
print(f"Audio format    : {audio_format}")
print(f"Device          : {device}")
print(f"Use TOC         : {use_toc}")
print(f"Extract mode    : {extract_mode}")

extract_book(
    input_path,
    use_toc=use_toc,
    extract_mode=extract_mode,
    output_dir=extracted_dir,
)

generate_audiobooks_kokoro(
    input_dir=extracted_dir,
    output_dir=audio_dir,
    voice=voice,
    lang_code=voice[0],
    audio_format=audio_format,
    device=device,
)

# Combine all generated WAVs into a single file in the input PDF's folder.
audio_files = sorted(
    f for f in os.listdir(audio_dir) if f.lower().endswith(".wav")
)
if not audio_files:
    raise FileNotFoundError(f"No .wav files found in {audio_dir}")

chunks = []
sr = None
for fname in audio_files:
    path = os.path.join(audio_dir, fname)
    data, file_sr = sf.read(path, always_2d=False)
    if sr is None:
        sr = file_sr
    elif file_sr != sr:
        raise ValueError(f"Sample rate mismatch in {fname}: {file_sr} != {sr}")
    chunks.append(data)

combined = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
sf.write(final_output, combined, sr)
print(f"Combined WAV saved: {final_output}")
PY
  fi

  if [[ -s "$final_output" && -x "$SCRIPT_DIR/save_google_drive.sh" ]]; then
    "$SCRIPT_DIR/save_google_drive.sh" "$final_output" || true
  fi
}

if [[ -d "$INPUT_PATH" ]]; then
  mapfile -d '' pdfs < <(find "$INPUT_PATH" -type f -iname "*.pdf" -print0 | sort -z)
  if [[ "${#pdfs[@]}" -eq 0 ]]; then
    echo "Error: no PDF files found in folder: $INPUT_PATH" >&2
    exit 1
  fi
  for pdf in "${pdfs[@]}"; do
    process_pdf "$pdf"
  done
  exit 0
fi

if [[ ! -f "$INPUT_PATH" ]]; then
  echo "Error: file or folder not found: $INPUT_PATH" >&2
  exit 1
fi
process_pdf "$INPUT_PATH"
