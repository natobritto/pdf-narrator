#!/usr/bin/env bash
# Quick Reference - PDF Narrator Batch Processor

cat << 'EOF'

═══════════════════════════════════════════════════════════════════════
                        QUICK REFERENCE CARD
═══════════════════════════════════════════════════════════════════════

BASIC USAGE:
───────────────────────────────────────────────────────────────────────
  Single PDF:      python batch_processor.py book.pdf
  With voice:      python batch_processor.py book.pdf --voice am_liam
  Batch:           python batch_processor.py pdfs/ --batch
  With logging:    python batch_processor.py book.pdf --log-file output.log

RESUME & RECOVERY:
───────────────────────────────────────────────────────────────────────
  Resume:          python batch_processor.py book.pdf
                   (automatically resumes if interrupted)
  
  Check state:     cat .audiobook_state/book.json
  Clear state:     rm .audiobook_state/book.json
  Clear all:       rm -rf .audiobook_state/

TESTING:
───────────────────────────────────────────────────────────────────────
  Run tests:       python -m pytest test_batch_processor.py -v
  Demo:            python demo_batch_processor.py
  Help:            python batch_processor.py --help
  
  Test combo only: python batch_processor.py book.pdf \
                     --skip-extraction --skip-generation

MONITORING:
───────────────────────────────────────────────────────────────────────
  Watch logs:      tail -f audiobook.log
  Check memory:    watch -n 5 'free -h'
  Count jobs:      ls .audiobook_state/ | wc -l
  Check progress:  ls audiobooks/*/*.wav | wc -l

LONG-RUNNING JOBS:
───────────────────────────────────────────────────────────────────────
  Start screen:    screen -S audiobooks
  Run batch:       python batch_processor.py pdfs/ --batch \
                     --log-file batch.log
  Detach:          Ctrl+A, D
  Reattach:        screen -r audiobooks
  List sessions:   screen -ls

TROUBLESHOOTING:
───────────────────────────────────────────────────────────────────────
  Job stuck:       rm .audiobook_state/job.json && retry
  Memory issues:   Edit batch_processor.py line ~360, reduce chunk_size
  Failed files:    Check --max-retries (default: 3)
  Verify audio:    ffmpeg -v error -i file.wav -f null -

FILE STRUCTURE:
───────────────────────────────────────────────────────────────────────
  extracted_books/    → Text extracted from PDFs
  audiobooks/         → Individual WAV files per chunk
  .audiobook_state/   → Job state files (JSON)
  *.wav (in PDF dir)  → Final combined audiobooks

COMMON OPTIONS:
───────────────────────────────────────────────────────────────────────
  --voice VOICE          Override voice pack
  --batch                Process directory
  --no-resume            Don't resume (start fresh)
  --stop-on-error        Stop batch on first error
  --max-retries N        Max retry attempts (default: 3)
  --skip-extraction      Skip text extraction
  --skip-generation      Skip audio generation
  --log-file FILE        Log to file
  --config FILE          Use custom config.json
  --state-dir DIR        Custom state directory

DOCUMENTATION:
───────────────────────────────────────────────────────────────────────
  README_BATCH_PROCESSOR.md    - Full user guide
  REFACTORING_SUMMARY.md       - Technical details
  MIGRATION_CHECKLIST.md       - Migration steps
  batch_processor.py --help    - CLI help

BACKWARD COMPATIBILITY:
───────────────────────────────────────────────────────────────────────
  Old:             ./genpdfaudio.sh book.pdf am_liam
  New (simple):    ./genpdfaudio_simple.sh book.pdf am_liam
  New (full):      python batch_processor.py book.pdf --voice am_liam

PERFORMANCE:
───────────────────────────────────────────────────────────────────────
  Extraction:      ~30s per book
  Generation:      ~40-50s per minute of audio
  Combination:     ~1 min per 12 hours of audio
  Memory:          ~170 MB (down from 16+ GB)

═══════════════════════════════════════════════════════════════════════
EOF
