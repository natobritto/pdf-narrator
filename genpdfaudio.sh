#!/usr/bin/env bash
#
# DEPRECATED: This script has been replaced by batch_processor.py
# Please use: python batch_processor.py [options]
# Or use the simple wrapper: ./genpdfaudio_simple.sh
#
# This script is kept for backward compatibility but forwards to the new system.
#

set -euo pipefail

echo "⚠️  NOTICE: genpdfaudio.sh is deprecated"
echo "   Please use: python batch_processor.py --help"
echo "   Or use simple wrapper: ./genpdfaudio_simple.sh"
echo ""
echo "   Forwarding to new batch processor..."
echo ""

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
cd "$SCRIPT_DIR"

# Forward to new batch processor
CMD="python batch_processor.py \"$INPUT_PATH\""

if [[ -n "$VOICE_OVERRIDE" ]]; then
  CMD="$CMD --voice \"$VOICE_OVERRIDE\""
fi

if [[ -d "$INPUT_PATH" ]]; then
  CMD="$CMD --batch"
fi

# Add timestamped log file
LOG_FILE="audiobook_$(date +%Y%m%d_%H%M%S).log"
CMD="$CMD --log-file \"$LOG_FILE\""

echo "Forwarding to: $CMD"
echo "Log file: $LOG_FILE"
echo ""

eval $CMD
exit $?

# ======================================================================
# OLD IMPLEMENTATION BELOW - KEPT FOR REFERENCE ONLY
# ======================================================================
process_pdf_old() {
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

print(f"Combining {len(audio_files)} audio files into: {final_output}")

# Memory-efficient approach: stream audio in chunks instead of loading everything
CHUNK_SIZE = 50  # Process 50 files at a time to avoid OOM
sr = None
total_samples = 0

# First pass: verify sample rates and count total samples
print("Verifying audio files and calculating total length...")
for fname in audio_files:
    path = os.path.join(audio_dir, fname)
    info = sf.info(path)
    if sr is None:
        sr = info.samplerate
    elif info.samplerate != sr:
        raise ValueError(f"Sample rate mismatch in {fname}: {info.samplerate} != {sr}")
    total_samples += info.frames

print(f"Total samples: {total_samples}, sample rate: {sr}, duration: {total_samples/sr:.1f}s")

# Second pass: stream and concatenate in chunks
print(f"Streaming audio in chunks of {CHUNK_SIZE} files...")
with sf.SoundFile(final_output, 'w', sr, channels=1, subtype='PCM_16') as outfile:
    for i in range(0, len(audio_files), CHUNK_SIZE):
        chunk_files = audio_files[i:i+CHUNK_SIZE]
        print(f"  Processing chunk {i//CHUNK_SIZE + 1}/{(len(audio_files) + CHUNK_SIZE - 1)//CHUNK_SIZE} ({len(chunk_files)} files)...")
        
        # Load and concatenate this chunk
        chunk_data = []
        for fname in chunk_files:
            path = os.path.join(audio_dir, fname)
            data, _ = sf.read(path, always_2d=False, dtype='float32')  # Use float32 to save memory
            chunk_data.append(data)
        
        # Concatenate chunk and write
        combined_chunk = np.concatenate(chunk_data) if len(chunk_data) > 1 else chunk_data[0]
        outfile.write(combined_chunk)
        
        # Clear memory
        del chunk_data, combined_chunk

print(f"Combined WAV saved: {final_output}")
PY
  fi

  if [[ -s "$final_output" && -x "$SCRIPT_DIR/save_google_drive.sh" ]]; then
    "$SCRIPT_DIR/save_google_drive.sh" "$final_output" || true
  fi
}

# Old batch processing logic - no longer used
if_old_implementation() {
  if [[ -d "$INPUT_PATH" ]]; then
    mapfile -d '' pdfs < <(find "$INPUT_PATH" -type f -iname "*.pdf" -print0 | sort -z)
    if [[ "${#pdfs[@]}" -eq 0 ]]; then
      echo "Error: no PDF files found in folder: $INPUT_PATH" >&2
      exit 1
    fi
    for pdf in "${pdfs[@]}"; do
      process_pdf_old "$pdf"
    done
    exit 0
  fi

  if [[ ! -f "$INPUT_PATH" ]]; then
    echo "Error: file or folder not found: $INPUT_PATH" >&2
    exit 1
  fi
  process_pdf_old "$INPUT_PATH"
}
