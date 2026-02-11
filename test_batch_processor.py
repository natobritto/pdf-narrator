#!/usr/bin/env python3
"""
Tests for batch_processor.py

Run with: python -m pytest test_batch_processor.py -v
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pytest
import soundfile as sf

from batch_processor import (
    JobState,
    StateManager,
    AudioCombiner,
    AudiobookProcessor,
)


class TestJobState:
    """Test JobState dataclass"""
    
    def test_creation(self):
        job = JobState(
            input_path="/path/to/file.pdf",
            output_path="/path/to/file.wav",
            status="pending"
        )
        assert job.input_path == "/path/to/file.pdf"
        assert job.status == "pending"
        assert job.retry_count == 0
    
    def test_to_dict(self):
        job = JobState(
            input_path="/path/to/file.pdf",
            output_path="/path/to/file.wav",
            status="completed",
            extraction_done=True
        )
        data = job.to_dict()
        assert data["status"] == "completed"
        assert data["extraction_done"] is True
    
    def test_from_dict(self):
        data = {
            "input_path": "/path/to/file.pdf",
            "output_path": "/path/to/file.wav",
            "status": "generating",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "error": None,
            "extraction_done": True,
            "generation_done": False,
            "combination_done": False,
            "retry_count": 1,
        }
        job = JobState.from_dict(data)
        assert job.status == "generating"
        assert job.retry_count == 1


class TestStateManager:
    """Test StateManager"""
    
    def test_save_and_load_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            manager = StateManager(state_dir)
            
            job = JobState(
                input_path="/test/book.pdf",
                output_path="/test/book.wav",
                status="generating"
            )
            
            manager.save_state(job)
            loaded = manager.load_state("/test/book.pdf")
            
            assert loaded is not None
            assert loaded.status == "generating"
            assert loaded.input_path == "/test/book.pdf"
    
    def test_load_nonexistent_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            manager = StateManager(state_dir)
            
            loaded = manager.load_state("/nonexistent.pdf")
            assert loaded is None
    
    def test_delete_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            manager = StateManager(state_dir)
            
            job = JobState(
                input_path="/test/book.pdf",
                output_path="/test/book.wav",
                status="completed"
            )
            
            manager.save_state(job)
            assert manager.load_state("/test/book.pdf") is not None
            
            manager.delete_state("/test/book.pdf")
            assert manager.load_state("/test/book.pdf") is None


class TestAudioCombiner:
    """Test AudioCombiner"""
    
    def create_test_wav(self, path: Path, duration_sec: float = 1.0, sr: int = 24000):
        """Create a test WAV file"""
        samples = int(duration_sec * sr)
        data = np.random.randn(samples).astype(np.float32) * 0.1
        sf.write(path, data, sr)
    
    def test_combine_audio_files_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir) / "audio"
            audio_dir.mkdir()
            
            # Create test audio files
            self.create_test_wav(audio_dir / "001.wav", 0.5)
            self.create_test_wav(audio_dir / "002.wav", 0.5)
            self.create_test_wav(audio_dir / "003.wav", 0.5)
            
            output_path = Path(tmpdir) / "combined.wav"
            combiner = AudioCombiner(chunk_size=2)
            
            success = combiner.combine_audio_files(audio_dir, output_path)
            
            assert success
            assert output_path.exists()
            
            # Verify output
            info = sf.info(output_path)
            assert info.samplerate == 24000
            assert info.frames > 0
    
    def test_combine_audio_files_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir) / "audio"
            audio_dir.mkdir()
            
            output_path = Path(tmpdir) / "combined.wav"
            combiner = AudioCombiner()
            
            success = combiner.combine_audio_files(audio_dir, output_path)
            
            assert not success
            assert not output_path.exists()
    
    def test_combine_audio_files_sample_rate_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir) / "audio"
            audio_dir.mkdir()
            
            # Create files with different sample rates
            self.create_test_wav(audio_dir / "001.wav", 0.5, sr=24000)
            self.create_test_wav(audio_dir / "002.wav", 0.5, sr=22050)
            
            output_path = Path(tmpdir) / "combined.wav"
            combiner = AudioCombiner()
            
            success = combiner.combine_audio_files(audio_dir, output_path)
            
            assert not success
    
    def test_combine_with_progress_callback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir) / "audio"
            audio_dir.mkdir()
            
            for i in range(5):
                self.create_test_wav(audio_dir / f"{i:03d}.wav", 0.1)
            
            output_path = Path(tmpdir) / "combined.wav"
            combiner = AudioCombiner(chunk_size=2)
            
            progress_calls = []
            
            def progress_cb(current, total):
                progress_calls.append((current, total))
            
            success = combiner.combine_audio_files(
                audio_dir, output_path, progress_callback=progress_cb
            )
            
            assert success
            assert len(progress_calls) > 0


class TestAudiobookProcessor:
    """Test AudiobookProcessor"""
    
    @patch('batch_processor.extract_book')
    @patch('batch_processor.generate_audiobooks_kokoro')
    def test_process_pdf_success(self, mock_generate, mock_extract):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_text("dummy")
            
            audio_dir = Path.cwd() / "audiobooks" / "test"
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            # Create dummy audio files
            for i in range(3):
                wav_path = audio_dir / f"{i:03d}.wav"
                data = np.random.randn(24000).astype(np.float32) * 0.1
                sf.write(wav_path, data, 24000)
            
            state_dir = Path(tmpdir) / ".state"
            processor = AudiobookProcessor(state_dir=state_dir)
            
            # Process
            success = processor.process_pdf(pdf_path, resume=False)
            
            # Verify
            assert success
            assert mock_extract.called
            assert mock_generate.called
            
            output_path = pdf_path.parent / "test.wav"
            assert output_path.exists()
    
    def test_process_pdf_already_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_text("dummy")
            
            output_path = pdf_path.parent / "test.wav"
            output_path.write_text("dummy audio")
            
            state_dir = Path(tmpdir) / ".state"
            processor = AudiobookProcessor(state_dir=state_dir)
            
            # Process
            success = processor.process_pdf(pdf_path)
            
            # Should skip because output exists
            assert success
    
    @patch('batch_processor.extract_book')
    def test_process_pdf_with_error(self, mock_extract):
        mock_extract.side_effect = Exception("Test error")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_text("dummy")
            
            state_dir = Path(tmpdir) / ".state"
            processor = AudiobookProcessor(state_dir=state_dir, max_retries=2)
            
            success = processor.process_pdf(pdf_path, resume=False)
            
            assert not success
            
            # Check state was saved
            job = processor.state_manager.load_state(str(pdf_path))
            assert job is not None
            assert job.status == "failed"
            assert job.retry_count == 1
    
    def test_process_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy PDFs
            pdf_paths = []
            for i in range(3):
                pdf_path = Path(tmpdir) / f"test{i}.pdf"
                pdf_path.write_text("dummy")
                
                # Pre-create output to simulate completion
                output_path = pdf_path.parent / f"test{i}.wav"
                output_path.write_text("dummy audio")
                
                pdf_paths.append(pdf_path)
            
            state_dir = Path(tmpdir) / ".state"
            processor = AudiobookProcessor(state_dir=state_dir)
            
            stats = processor.process_batch(pdf_paths, resume=False)
            
            assert stats["total"] == 3
            assert stats["completed"] == 3
            assert stats["failed"] == 0


def test_state_manager_get_job_id():
    """Test job ID generation"""
    manager = StateManager(Path("/tmp"))
    
    job_id1 = manager._get_job_id("/path/to/book.pdf")
    job_id2 = manager._get_job_id("/other/path/book.pdf")
    job_id3 = manager._get_job_id("/path/to/other.pdf")
    
    assert job_id1 == job_id2  # Same filename
    assert job_id1 != job_id3  # Different filename


def test_audio_combiner_chunk_size():
    """Test that chunk size is respected"""
    combiner = AudioCombiner(chunk_size=10)
    assert combiner.chunk_size == 10
    
    combiner = AudioCombiner(chunk_size=100)
    assert combiner.chunk_size == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
