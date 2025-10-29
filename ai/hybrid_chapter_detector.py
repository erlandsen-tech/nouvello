"""
EPUB Chapter Extraction
Uses native EPUB structure (TOC/spine) to get chapters. No AI needed.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.epub_parser import EPUBParser
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class HybridResult:
    """Result from hybrid chapter detection"""
    chapters: List[List[str]]
    headings: List[str]
    confidence: float
    method_used: str
    fallback_used: bool
    metadata: Dict[str, Any]

class HybridChapterDetector:
    """EPUB-only chapter detector using EPUB structure"""
    
    def __init__(self):
        pass
    
    def detect_chapters(self, file_path: str) -> HybridResult:
        """Detect chapters using hybrid approach with graceful degradation"""
        
        print("Starting EPUB chapter extraction...")
        
        # Only EPUB is supported
        file_ext = Path(file_path).suffix.lower()
        if file_ext != '.epub':
            print("Non-EPUB file provided. Returning fallback single-chapter result.")
            return self._create_fallback_result(file_path)
        
        return self._detect_chapters_epub(file_path)
    
    def _detect_chapters_epub(self, file_path: str) -> HybridResult:
        """Detect chapters from EPUB file using native structure"""
        print("Detecting EPUB file format...")
        
        try:
            parser = EPUBParser(file_path)
            chapters = parser.parse()
            
            if not chapters:
                print("EPUB parsing returned no chapters, using fallback")
                return self._create_fallback_result(file_path)
            
            print(f"EPUB parser found {len(chapters)} chapters")
            
            # Convert EPUB chapters to hybrid result format
            chapter_lines = []
            headings = []
            
            for epub_chapter in chapters:
                headings.append(epub_chapter.title)
                # Split content into lines
                lines = epub_chapter.content.split('\n')
                chapter_lines.append(lines)
            
            return HybridResult(
                chapters=chapter_lines,
                headings=headings,
                confidence=1.0,  # EPUB structure is highly reliable
                method_used='epub_native',
                fallback_used=False,
                metadata={
                    'num_chapters': len(chapters),
                    'source': 'epub_toc_or_spine',
                    'file_format': 'epub'
                }
            )
            
        except Exception as e:
            print(f"EPUB detection failed: {e}")
            return self._create_fallback_result(file_path)
    
    def _create_fallback_result(self, file_path: str) -> HybridResult:
        """Create fallback result when both methods fail"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        return HybridResult(
            chapters=[lines],
            headings=[],
            confidence=0.1,
            method_used='fallback',
            fallback_used=True,
            metadata={'reason': 'Both traditional and AI detection failed'}
        )

def main():
    """Example usage of EPUB-only detector"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EPUB Chapter Extraction')
    parser.add_argument('book_path', help='Path to the EPUB file (.epub)')
    
    args = parser.parse_args()
    
    detector = HybridChapterDetector()
    
    result = detector.detect_chapters(args.book_path)
    
    print(f"\nHybrid Detection Results:")
    print(f"Chapters found: {len(result.chapters)}")
    print(f"Method used: {result.method_used}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Fallback used: {result.fallback_used}")
    print(f"Headings: {result.headings[:5]}...")

if __name__ == "__main__":
    main()
