#!/usr/bin/env python3
"""
Batch PDF to Audiobook Processor

Production-ready audiobook generation with:
- Resume capability for long-running jobs
- Progress tracking and state management
- Error recovery and retry logic
- Memory-efficient audio combination
- Detailed logging and auditing
"""

import argparse
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
import soundfile as sf
import torch

from extract import extract_book
from generate_audiobook_kokoro import generate_audiobooks_kokoro


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class JobState:
    """State tracking for audiobook generation jobs"""
    input_path: str
    output_path: str
    status: str  # pending, extracting, generating, combining, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    extraction_done: bool = False
    generation_done: bool = False
    combination_done: bool = False
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobState':
        return cls(**data)


class StateManager:
    """Manages job state persistence for resume capability"""
    
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(exist_ok=True)
    
    def save_state(self, job: JobState):
        """Save job state to disk"""
        state_file = self.state_dir / f"{self._get_job_id(job.input_path)}.json"
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(job.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state for {job.input_path}: {e}")
    
    def load_state(self, input_path: str) -> Optional[JobState]:
        """Load job state from disk"""
        state_file = self.state_dir / f"{self._get_job_id(input_path)}.json"
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return JobState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load state for {input_path}: {e}")
            return None
    
    def delete_state(self, input_path: str):
        """Delete job state file"""
        state_file = self.state_dir / f"{self._get_job_id(input_path)}.json"
        if state_file.exists():
            state_file.unlink()
    
    @staticmethod
    def _get_job_id(input_path: str) -> str:
        """Generate unique job ID from input path"""
        return Path(input_path).stem


class AudioCombiner:
    """Memory-efficient audio file combiner"""
    
    def __init__(self, chunk_size: int = 50):
        self.chunk_size = chunk_size
    
    def combine_audio_files(
        self,
        audio_dir: Path,
        output_path: Path,
        progress_callback=None
    ) -> bool:
        """
        Combine multiple WAV files into one using streaming approach
        
        Args:
            audio_dir: Directory containing WAV files
            output_path: Output file path
            progress_callback: Optional callback(current, total)
        
        Returns:
            True if successful
        """
        audio_files = sorted(audio_dir.glob("*.wav"))
        
        if not audio_files:
            logger.error(f"No WAV files found in {audio_dir}")
            return False
        
        logger.info(f"Combining {len(audio_files)} audio files into: {output_path}")
        
        try:
            # First pass: verify sample rates and count total samples
            logger.info("Verifying audio files...")
            sr = None
            total_samples = 0
            
            for audio_file in audio_files:
                info = sf.info(audio_file)
                if sr is None:
                    sr = info.samplerate
                elif info.samplerate != sr:
                    raise ValueError(
                        f"Sample rate mismatch in {audio_file.name}: "
                        f"{info.samplerate} != {sr}"
                    )
                total_samples += info.frames
            
            duration = total_samples / sr
            logger.info(
                f"Total samples: {total_samples}, sample rate: {sr}, "
                f"duration: {duration:.1f}s ({duration/3600:.1f}h)"
            )
            
            # Second pass: stream and concatenate in chunks
            logger.info(f"Streaming audio in chunks of {self.chunk_size} files...")
            num_chunks = (len(audio_files) + self.chunk_size - 1) // self.chunk_size
            
            with sf.SoundFile(
                output_path, 'w', sr, channels=1, subtype='PCM_16'
            ) as outfile:
                for i in range(0, len(audio_files), self.chunk_size):
                    chunk_files = audio_files[i:i + self.chunk_size]
                    chunk_num = i // self.chunk_size + 1
                    
                    logger.info(
                        f"  Chunk {chunk_num}/{num_chunks} "
                        f"({len(chunk_files)} files)..."
                    )
                    
                    if progress_callback:
                        progress_callback(i, len(audio_files))
                    
                    # Load and concatenate this chunk
                    chunk_data = []
                    for audio_file in chunk_files:
                        data, _ = sf.read(
                            audio_file,
                            always_2d=False,
                            dtype='float32'  # Half memory of float64
                        )
                        chunk_data.append(data)
                    
                    # Concatenate and write
                    combined_chunk = (
                        np.concatenate(chunk_data)
                        if len(chunk_data) > 1
                        else chunk_data[0]
                    )
                    outfile.write(combined_chunk)
                    
                    # Explicit cleanup
                    del chunk_data, combined_chunk
            
            logger.info(f"✓ Combined WAV saved: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to combine audio files: {e}")
            logger.error(traceback.format_exc())
            return False


class AudiobookProcessor:
    """Main audiobook processing engine"""
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        state_dir: Optional[Path] = None,
        max_retries: int = 3
    ):
        self.config = self._load_config(config_path or Path("config.json"))
        self.state_manager = StateManager(
            state_dir or Path.cwd() / ".audiobook_state"
        )
        self.audio_combiner = AudioCombiner(chunk_size=50)
        self.max_retries = max_retries
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def process_pdf(
        self,
        input_path: Path,
        voice_override: Optional[str] = None,
        resume: bool = True,
        skip_extraction: bool = False,
        skip_generation: bool = False
    ) -> bool:
        """
        Process a single PDF into audiobook
        
        Args:
            input_path: Path to PDF file
            voice_override: Override voice from config
            resume: Resume from previous state if available
            skip_extraction: Skip text extraction (for testing)
            skip_generation: Skip audio generation (for testing)
        
        Returns:
            True if successful
        """
        input_path = input_path.resolve()
        base_name = input_path.stem
        output_path = input_path.parent / f"{base_name}.wav"
        
        # Check if already completed
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"✓ Already completed (skipping): {output_path}")
            return True
        
        # Load or create job state
        job = self.state_manager.load_state(str(input_path))
        if job and resume:
            logger.info(f"Resuming job from state: {job.status}")
        else:
            job = JobState(
                input_path=str(input_path),
                output_path=str(output_path),
                status="pending",
                started_at=datetime.now().isoformat()
            )
        
        # Setup directories
        extracted_dir = Path.cwd() / "extracted_books" / base_name
        audio_dir = Path.cwd() / "audiobooks" / base_name
        
        # Get configuration
        source_cfg = self.config.get("source_settings", {}) or {}
        audio_cfg = self.config.get("audio_settings", {}) or {}
        
        use_toc = bool(source_cfg.get("use_toc", True))
        extract_mode = source_cfg.get("extract_mode", "chapters")
        voice = voice_override or audio_cfg.get("voicepack") or "am_liam"
        lang_code = voice[0] if voice else "a"
        audio_format = ".wav"
        
        requested_device = audio_cfg.get("device")

        if requested_device:
            device = requested_device
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"torch.cuda.is_available(): {torch.cuda.is_available()}")
        logger.info(f"Selected device: {device}")

        logger.info(f"Processing: {input_path.name}")
        logger.info(f"  Output: {output_path}")
        logger.info(f"  Voice: {voice}, Language: {lang_code}, Device: {device}")
        
        try:
            # Phase 1: Text Extraction
            if not job.extraction_done and not skip_extraction:
                logger.info("Phase 1/3: Extracting text...")
                job.status = "extracting"
                self.state_manager.save_state(job)
                
                extract_book(
                    str(input_path),
                    use_toc=use_toc,
                    extract_mode=extract_mode,
                    output_dir=str(extracted_dir)
                )
                
                job.extraction_done = True
                self.state_manager.save_state(job)
                logger.info("✓ Text extraction complete")
            else:
                logger.info("Phase 1/3: Text extraction (skipped)")
            
            # Phase 2: Audio Generation
            if not job.generation_done and not skip_generation:
                logger.info("Phase 2/3: Generating audio...")
                job.status = "generating"
                self.state_manager.save_state(job)
                
                generate_audiobooks_kokoro(
                    input_dir=str(extracted_dir),
                    output_dir=str(audio_dir),
                    voice=voice,
                    lang_code=lang_code,
                    audio_format=audio_format,
                    device=device
                )
                
                job.generation_done = True
                self.state_manager.save_state(job)
                logger.info("✓ Audio generation complete")
            else:
                logger.info("Phase 2/3: Audio generation (skipped)")
            
            # Phase 3: Audio Combination
            if not job.combination_done:
                logger.info("Phase 3/3: Combining audio files...")
                job.status = "combining"
                self.state_manager.save_state(job)
                
                success = self.audio_combiner.combine_audio_files(
                    audio_dir, output_path
                )
                
                if not success:
                    raise RuntimeError("Audio combination failed")
                
                job.combination_done = True
                job.status = "completed"
                job.completed_at = datetime.now().isoformat()
                self.state_manager.save_state(job)
                logger.info("✓ Audio combination complete")
            else:
                logger.info("Phase 3/3: Audio combination (skipped)")
            
            # Cleanup state on success
            self.state_manager.delete_state(str(input_path))
            
            logger.info(f"✓✓✓ Successfully completed: {output_path}")
            return True
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.retry_count += 1
            self.state_manager.save_state(job)
            
            logger.error(f"✗ Failed to process {input_path.name}: {e}")
            logger.error(traceback.format_exc())
            
            # Retry logic
            if job.retry_count < self.max_retries:
                logger.info(
                    f"Will retry ({job.retry_count}/{self.max_retries}) "
                    f"on next run"
                )
            else:
                logger.error(f"Max retries exceeded for {input_path.name}")
            
            return False
    
    def process_batch(
        self,
        input_paths: List[Path],
        voice_override: Optional[str] = None,
        resume: bool = True,
        continue_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        Process multiple PDFs in batch
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(input_paths),
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "started_at": datetime.now().isoformat(),
        }
        
        logger.info(f"Starting batch processing of {len(input_paths)} files")
        
        for i, pdf_path in enumerate(input_paths, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i}/{len(input_paths)}] Processing: {pdf_path.name}")
            logger.info(f"{'='*60}")
            
            try:
                success = self.process_pdf(pdf_path, voice_override, resume)
                if success:
                    stats["completed"] += 1
                else:
                    stats["failed"] += 1
                    if not continue_on_error:
                        logger.error("Stopping batch due to error")
                        break
            except Exception as e:
                logger.error(f"Unexpected error processing {pdf_path.name}: {e}")
                logger.error(traceback.format_exc())
                stats["failed"] += 1
                if not continue_on_error:
                    break
        
        stats["completed_at"] = datetime.now().isoformat()
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total files:     {stats['total']}")
        logger.info(f"Completed:       {stats['completed']}")
        logger.info(f"Failed:          {stats['failed']}")
        logger.info(f"Success rate:    {stats['completed']/stats['total']*100:.1f}%")
        
        return stats


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="PDF to Audiobook Batch Processor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single PDF
  python batch_processor.py book.pdf
  
  # Process with voice override
  python batch_processor.py book.pdf --voice am_liam
  
  # Process entire directory
  python batch_processor.py pdfs/ --batch
  
  # Resume previous job
  python batch_processor.py book.pdf --resume
  
  # Test combination only (skip extraction/generation)
  python batch_processor.py book.pdf --skip-extraction --skip-generation
        """
    )
    
    parser.add_argument(
        "input",
        type=Path,
        help="PDF file or directory to process"
    )
    
    parser.add_argument(
        "--voice",
        type=str,
        help="Voice pack override (e.g., am_liam)"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all PDFs in directory"
    )
    
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Don't resume from saved state"
    )
    
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop batch processing on first error"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Config file path (default: config.json)"
    )
    
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(".audiobook_state"),
        help="State directory for resume capability"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retry attempts per file (default: 3)"
    )
    
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip text extraction (for testing)"
    )
    
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip audio generation (for testing)"
    )
    
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log to file in addition to console"
    )
    
    args = parser.parse_args()
    
    # Setup file logging if requested
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        logger.addHandler(file_handler)
    
    # Validate input
    if not args.input.exists():
        logger.error(f"Input not found: {args.input}")
        return 1
    
    # Initialize processor
    processor = AudiobookProcessor(
        config_path=args.config,
        state_dir=args.state_dir,
        max_retries=args.max_retries
    )
    
    # Process
    if args.input.is_dir() or args.batch:
        if args.input.is_file():
            logger.error("--batch requires a directory input")
            return 1
        
        pdf_files = sorted(args.input.glob("*.pdf"))
        if not pdf_files:
            logger.error(f"No PDF files found in {args.input}")
            return 1
        
        stats = processor.process_batch(
            pdf_files,
            voice_override=args.voice,
            resume=not args.no_resume,
            continue_on_error=not args.stop_on_error
        )
        
        return 0 if stats["failed"] == 0 else 1
    else:
        if not args.input.is_file():
            logger.error(f"Input is not a file: {args.input}")
            return 1
        
        success = processor.process_pdf(
            args.input,
            voice_override=args.voice,
            resume=not args.no_resume,
            skip_extraction=args.skip_extraction,
            skip_generation=args.skip_generation
        )
        
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
