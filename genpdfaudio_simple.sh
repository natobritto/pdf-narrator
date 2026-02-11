#!/usr/bin/env bash
#
# Simple wrapper for batch_processor.py
# Maintains backward compatibility with old genpdfaudio.sh
#

set -euo pipefail

usage() {
  echo "Usage: $0 <file>.pdf|<folder> [voicepack]" >&2
  echo "Example: $0 ./book.pdf am_liam" >&2
  echo "Example: $0 ./pdfs/ am_liam" >&2
  echo ""
  echo "This is a simple wrapper for batch_processor.py"
  echo "For advanced options, use: python batch_processor.py --help"
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

INPUT="$1"
VOICE="${2:-}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Build command
CMD="python batch_processor.py \"$INPUT\""

if [[ -n "$VOICE" ]]; then
  CMD="$CMD --voice \"$VOICE\""
fi

if [[ -d "$INPUT" ]]; then
  CMD="$CMD --batch"
fi

# Add logging
LOG_FILE="audiobook_$(date +%Y%m%d_%H%M%S).log"
CMD="$CMD --log-file \"$LOG_FILE\""

echo "Starting audiobook generation..."
echo "Logs will be written to: $LOG_FILE"
echo ""

eval $CMD
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
  echo ""
  echo "✓ Audiobook generation completed successfully!"
  echo "Check log file for details: $LOG_FILE"
else
  echo ""
  echo "✗ Audiobook generation failed!"
  echo "Check log file for errors: $LOG_FILE"
fi

exit $EXIT_CODE
