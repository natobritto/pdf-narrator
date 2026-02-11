#!/usr/bin/env python3
"""
Quick demonstration of batch_processor.py capabilities
Run this to verify the installation and see usage examples
"""

import sys
from pathlib import Path

print("=" * 70)
print("PDF-Narrator Batch Processor - Quick Start Guide")
print("=" * 70)
print()

# Check if batch_processor exists
if not Path("batch_processor.py").exists():
    print("❌ Error: batch_processor.py not found in current directory")
    sys.exit(1)

print("✓ batch_processor.py found")
print()

print("USAGE EXAMPLES:")
print("-" * 70)
print()

print("1. Process a single PDF:")
print("   $ python batch_processor.py book.pdf")
print()

print("2. Process with specific voice:")
print("   $ python batch_processor.py book.pdf --voice am_liam")
print()

print("3. Process entire directory:")
print("   $ python batch_processor.py pdfs/ --batch")
print()

print("4. Resume interrupted job:")
print("   $ python batch_processor.py book.pdf --resume")
print()

print("5. Test audio combination only (if audio files exist):")
print("   $ python batch_processor.py book.pdf \\")
print("       --skip-extraction --skip-generation")
print()

print("6. Process with logging:")
print("   $ python batch_processor.py book.pdf --log-file output.log")
print()

print("7. Long-running batch with screen:")
print("   $ screen -S audiobooks")
print("   $ python batch_processor.py pdfs/ --batch --log-file batch.log")
print("   # Press Ctrl+A, D to detach")
print("   # Later: screen -r audiobooks")
print()

print("-" * 70)
print()

print("KEY FEATURES:")
print("-" * 70)
print("  ✓ Automatic resume on interruption")
print("  ✓ Memory-efficient (handles 12+ hour audiobooks)")
print("  ✓ Error recovery with configurable retries")
print("  ✓ Progress tracking and detailed logging")
print("  ✓ State management for auditing")
print("  ✓ Comprehensive test suite")
print()

print("-" * 70)
print()

print("TESTING:")
print("-" * 70)
print("Run tests to verify installation:")
print("   $ python -m pytest test_batch_processor.py -v")
print()

print("-" * 70)
print()

print("DOCUMENTATION:")
print("-" * 70)
print("See README_BATCH_PROCESSOR.md for comprehensive documentation")
print()

print("Full help:")
print("   $ python batch_processor.py --help")
print()

print("=" * 70)
print()

# Try importing dependencies
print("Checking dependencies...")
try:
    import numpy as np
    print("  ✓ numpy")
except ImportError:
    print("  ❌ numpy - run: pip install numpy")

try:
    import soundfile as sf
    print("  ✓ soundfile")
except ImportError:
    print("  ❌ soundfile - run: pip install soundfile")

try:
    import pytest
    print("  ✓ pytest")
except ImportError:
    print("  ⚠ pytest (optional for testing) - run: pip install pytest")

print()

# Check for existing state
state_dir = Path(".audiobook_state")
if state_dir.exists():
    state_files = list(state_dir.glob("*.json"))
    if state_files:
        print(f"📋 Found {len(state_files)} saved job state(s):")
        for state_file in state_files[:5]:  # Show first 5
            print(f"   - {state_file.stem}")
        if len(state_files) > 5:
            print(f"   ... and {len(state_files) - 5} more")
        print()
        print("   These jobs can be resumed automatically.")
        print()

print("Ready to process audiobooks! 🎧")
print()
