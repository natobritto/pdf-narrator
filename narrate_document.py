#!/usr/bin/env python3
"""
Wrapper for pdf-narrator to handle PDF input and convert to audiobook.
This script extracts text from PDF and generates audio using Kokoro TTS.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Add pdf-narrator to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from generate_audiobook_kokoro import test_single_voice_kokoro
except ImportError as e:
    print(f"Error: Could not import Kokoro narrator: {e}")
    sys.exit(1)


def extract_text_from_pdf(pdf_path: str, max_chars: int = 50000) -> str:
    """Extract text from PDF file."""
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                if len(text) > max_chars:
                    break
                text += page.extract_text() + "\n"
        return text[:max_chars]
    except ImportError:
        print("Warning: PyPDF2 not available, trying PyMuPDF...")
        try:
            import fitz
            text = ""
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc):
                if len(text) > max_chars:
                    break
                text += page.get_text() + "\n"
            doc.close()
            return text[:max_chars]
        except ImportError:
            print("Error: Neither PyPDF2 nor PyMuPDF available")
            sys.exit(1)


def extract_text_from_file(file_path: str, max_chars: int = 50000) -> str:
    """Extract text from various file formats."""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == ".pdf":
        return extract_text_from_pdf(file_path, max_chars)
    elif file_ext == ".txt":
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()[:max_chars]
    elif file_ext in [".epub"]:
        try:
            import ebooklib
            from ebooklib import epub
            book = epub.read_epub(file_path)
            text = ""
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    text += item.get_content().decode('utf-8', errors='ignore') + "\n"
            return text[:max_chars]
        except ImportError:
            print("Error: ebooklib not available for EPUB support")
            sys.exit(1)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")


def main():
    parser = argparse.ArgumentParser(description="Convert documents to audiobooks using Kokoro TTS")
    parser.add_argument("--input", required=True, help="Input file (PDF, TXT, EPUB)")
    parser.add_argument("--output", required=True, help="Output audio file path (MP3 or WAV)")
    parser.add_argument("--voice", default="af_bella", help="Voice ID (default: af_bella)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed (default: 1.0)")
    parser.add_argument("--lang", default="a", help="Language code for Kokoro (default: 'a' for English)")
    parser.add_argument("--device", default="cpu", help="Device to use: 'cpu' or 'cuda' (default: cpu)")
    parser.add_argument("--max-chars", type=int, default=50000, help="Maximum characters to process (default: 50000)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # Validate input
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting text from {input_path.name}...")
    try:
        text = extract_text_from_file(str(input_path), args.max_chars)
        
        if not text or len(text.strip()) < 10:
            print("Error: Could not extract meaningful text from input file")
            sys.exit(1)
        
        print(f"Extracted {len(text)} characters")
        print(f"Generating audio ({args.voice}, speed={args.speed})...")
        
        # Call the Kokoro narrator
        result = test_single_voice_kokoro(
            input_text=text,
            voice=args.voice,
            output_path=str(output_path),
            lang_code=args.lang,
            device=args.device,
            speed=args.speed,
        )
        
        if result:
            print(f"Success! Audio saved to: {output_path}")
            sys.exit(0)
        else:
            print("Error: Audio generation failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
