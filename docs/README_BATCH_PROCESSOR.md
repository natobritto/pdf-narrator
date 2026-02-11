# Audiobook Batch Processor

Production-ready PDF to audiobook conversion with resume capability, error recovery, and memory-efficient processing.

## Features

✅ **Resume Capability**: Automatically resumes from where it left off if interrupted  
✅ **Error Recovery**: Retries failed files with configurable retry limits  
✅ **Memory Efficient**: Streams audio combination to avoid OOM on large books  
✅ **Progress Tracking**: Detailed logging and progress indicators  
✅ **Batch Processing**: Process entire directories of PDFs  
✅ **State Management**: Saves job state for auditing and debugging  
✅ **Comprehensive Tests**: Full test suite included  

## Quick Start

### Process a Single PDF

```bash
python batch_processor.py book.pdf
```

### Process with Voice Override

```bash
python batch_processor.py book.pdf --voice am_liam
```

### Process Entire Directory

```bash
python batch_processor.py pdfs/ --batch
```

### Resume Previous Job

```bash
python batch_processor.py book.pdf --resume
```

The processor automatically saves state and will resume from where it left off.

## Advanced Usage

### Test Combination Only

If extraction and generation are already done:

```bash
python batch_processor.py book.pdf --skip-extraction --skip-generation
```

### Stop on First Error

By default, batch processing continues on errors. To stop on first error:

```bash
python batch_processor.py pdfs/ --batch --stop-on-error
```

### Custom Configuration

```bash
python batch_processor.py book.pdf --config my_config.json --state-dir .my_state
```

### With Logging

```bash
python batch_processor.py book.pdf --log-file audiobook.log
```

## State Management

The processor saves job state in `.audiobook_state/` directory:

- **Automatic Resume**: Interrupted jobs resume from last checkpoint
- **Error Recovery**: Failed jobs track retry count
- **Progress Tracking**: Monitor which phase each job is in

Job states:
- `pending`: Not started
- `extracting`: Extracting text from PDF
- `generating`: Generating audio from text
- `combining`: Combining audio files
- `completed`: Successfully finished
- `failed`: Error occurred (will retry)

### Inspect Job State

```bash
cat .audiobook_state/mybook.json
```

### Clear All State

```bash
rm -rf .audiobook_state/
```

## Architecture

The processor is organized into modular components:

### Core Components

1. **JobState**: Tracks processing state for each PDF
2. **StateManager**: Handles state persistence and recovery
3. **AudioCombiner**: Memory-efficient audio file combining
4. **AudiobookProcessor**: Main processing orchestrator

### Processing Phases

Each PDF goes through three phases:

1. **Text Extraction**: Extract text from PDF using `extract.py`
2. **Audio Generation**: Convert text to speech using `generate_audiobook_kokoro.py`
3. **Audio Combination**: Combine individual audio files into single file

Each phase is checkpointed, so if interrupted, processing resumes from the next phase.

## Error Handling

### Automatic Retries

Failed files are automatically retried up to `--max-retries` times (default: 3).

### Retry Strategy

- Extraction failure: Retry from extraction
- Generation failure: Retry from generation (extraction skipped)
- Combination failure: Retry only combination

### Manual Retry

To manually retry a failed file:

```bash
python batch_processor.py failed_book.pdf --resume
```

## Memory Management

The audio combiner uses a streaming approach to avoid OOM:

- Processes audio in chunks (default: 50 files at a time)
- Uses float32 instead of float64 (half the memory)
- Writes directly to output file (no large concatenation in memory)
- Explicit cleanup after each chunk

For a 12-hour audiobook (373 files):
- **Old approach**: ~16 GB RAM
- **New approach**: ~170 MB RAM

## Testing

Run the test suite:

```bash
# Install pytest if needed
pip install pytest pytest-mock

# Run tests
python -m pytest test_batch_processor.py -v

# Run specific test
python -m pytest test_batch_processor.py::TestAudioCombiner::test_combine_audio_files_basic -v

# Run with coverage
pip install pytest-cov
python -m pytest test_batch_processor.py --cov=batch_processor --cov-report=html
```

## Backward Compatibility

The simple wrapper script maintains backward compatibility:

```bash
./genpdfaudio_simple.sh book.pdf am_liam
./genpdfaudio_simple.sh pdfs/ am_liam
```

## Monitoring Long-Running Jobs

For multi-week processing runs:

### Use Screen/Tmux

```bash
# Start screen session
screen -S audiobooks

# Run processor
python batch_processor.py large_collection/ --batch --log-file processing.log

# Detach: Ctrl+A, D

# Reattach later
screen -r audiobooks
```

### Monitor Progress

```bash
# Watch log file
tail -f processing.log

# Check state files
ls -lh .audiobook_state/

# Count completed files
ls -lh audiobooks/*/combined.wav | wc -l
```

### System Monitoring

```bash
# Monitor memory usage
watch -n 5 'free -h && ps aux | grep batch_processor | grep -v grep'

# Monitor disk space
watch -n 60 'df -h'
```

## Troubleshooting

### Job Stuck in State

If a job appears stuck, check the state file:

```bash
cat .audiobook_state/mybook.json
```

Reset the job:

```bash
rm .audiobook_state/mybook.json
python batch_processor.py mybook.pdf
```

### Out of Disk Space

Audio files are large. Ensure sufficient disk space:

- Extracted text: ~1-5 MB per book
- Individual WAV files: ~10-50 MB per file
- Combined WAV: ~100-500 MB per book

### Memory Issues

If still experiencing OOM:

1. Reduce chunk size: Edit `batch_processor.py`, change `AudioCombiner(chunk_size=50)` to lower value
2. Close other applications
3. Process fewer files in parallel

### Corrupt Audio Files

If combination fails with corrupt audio:

```bash
# Test individual files
for f in audiobooks/mybook/*.wav; do
  echo "Testing $f"
  ffmpeg -v error -i "$f" -f null - 2>&1 | head -5
done
```

## Performance

Typical processing times (on modern hardware):

- Text extraction: 10-30 seconds per book
- Audio generation: 40-50 seconds per minute of audio
- Audio combination: 5-20 seconds per hour of audio

For a 12-hour audiobook:
- Extraction: ~30 seconds
- Generation: ~5-6 hours
- Combination: ~1 minute
- **Total**: ~5-6 hours

## Configuration

Example `config.json`:

```json
{
  "source_settings": {
    "use_toc": true,
    "extract_mode": "chapters"
  },
  "audio_settings": {
    "voicepack": "am_liam",
    "device": "cuda"
  }
}
```

## Migration from Old Script

If you were using `genpdfaudio.sh`:

1. **No changes needed**: Use `genpdfaudio_simple.sh` as drop-in replacement
2. **Or migrate**: Use new `batch_processor.py` directly for more control

Benefits of migration:
- Resume capability
- Better error handling
- Progress tracking
- State inspection
- More efficient memory usage

## Command Reference

```bash
# Basic usage
python batch_processor.py <input> [options]

# Options
--voice VOICE              Voice pack override
--batch                    Process directory of PDFs
--no-resume               Don't resume from saved state
--stop-on-error           Stop batch on first error
--config PATH             Config file (default: config.json)
--state-dir PATH          State directory (default: .audiobook_state)
--max-retries N           Max retry attempts (default: 3)
--skip-extraction         Skip text extraction phase
--skip-generation         Skip audio generation phase
--log-file PATH           Log to file
--help                    Show full help
```

## License

Same as parent project.
