"""
Hybrid Chapter Detection System
Combines traditional chapterize with AI detection for maximum accuracy
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_chapter_detector import AIChapterDetector, ChapterDetectionResult
from ai.epub_parser import EPUBParser
import chapterize.chapterize as ch
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
    """Combines traditional and AI chapter detection for best results"""
    
    def __init__(self, 
                 llm_provider: str = "bedrock",
                 api_key: Optional[str] = None,
                 region: Optional[str] = None,
                 profile: Optional[str] = None,
                 confidence_threshold: float = 0.7,
                 skip_ai: bool = False):
        self.ai_detector = AIChapterDetector(
            llm_provider=llm_provider,
            api_key=api_key,
            region=region,
            profile=profile
        )
        self.confidence_threshold = confidence_threshold
        self.skip_ai = skip_ai
    
    def detect_chapters(self, file_path: str) -> HybridResult:
        """Detect chapters using hybrid approach with graceful degradation"""
        
        print("Starting hybrid chapter detection...")
        
        # Check if it's an EPUB file
        file_ext = Path(file_path).suffix.lower()
        if file_ext == '.epub':
            return self._detect_chapters_epub(file_path)
        
        # Try traditional chapterize first (fast and reliable for plain text)
        print("Attempting traditional detection...")
        traditional_result = self._try_traditional_detection(file_path)
        
        # Try AI detection only if traditional worked or if explicitly requested
        ai_result = None
        if hasattr(self, 'skip_ai') and self.skip_ai:
            print("Skipping AI detection (--skip-ai flag)")
        elif self.ai_detector.llm_client is not None:
            print("Attempting AI detection...")
            ai_result = self._try_ai_detection(file_path)
        else:
            print("Skipping AI detection (no LLM client available)")
        
        # Choose best result based on confidence and quality
        if traditional_result and ai_result:
            print("Both methods succeeded, choosing best result...")
            return self._choose_best_result(traditional_result, ai_result)
        elif traditional_result:
            print("Using traditional detection result")
            return self._convert_traditional_result(traditional_result)
        elif ai_result:
            print("Using AI detection result")
            return self._convert_ai_result(ai_result)
        else:
            print("Both methods failed, using fallback")
            # Fallback: return entire text as single chapter
            return self._create_fallback_result(file_path)
    
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
            print("Falling back to text extraction and AI detection")
            return self._create_fallback_result(file_path)
    
    def _try_traditional_detection(self, file_path: str) -> Optional[Any]:
        """Try traditional chapterize detection"""
        try:
            book = ch.Book(file_path, nochapters=False, stats=False)
            # Check if chapterize found enough chapters (it exits if < 3)
            if hasattr(book, 'numChapters') and book.numChapters >= 3:
                return book
            else:
                print(f"Traditional detection found insufficient chapters ({getattr(book, 'numChapters', 0)})")
                return None
        except (SystemExit, BaseException) as e:
            # Chapterize calls exit() when it finds < 3 chapters
            if isinstance(e, SystemExit):
                print("Traditional detection failed: book has fewer than 3 chapters (chapterize limitation)")
            else:
                print(f"Traditional detection failed: {e}")
            return None
    
    def _try_ai_detection(self, file_path: str) -> Optional[ChapterDetectionResult]:
        """Try AI detection with timeout and fallback"""
        try:
            print("Attempting AI detection...")
            result = self.ai_detector.detect_chapters(file_path)
            
            # Validate AI result
            if result and result.chapters and len(result.chapters) > 0:
                print(f"AI detection successful: {len(result.chapters)} chapters found")
                return result
            else:
                print("AI detection returned empty result")
                return None
                
        except Exception as e:
            print(f"AI detection failed: {e}")
            print("Falling back to traditional detection only")
            return None
    
    def _choose_best_result(self, traditional: Any, ai: ChapterDetectionResult) -> HybridResult:
        """Choose the best result between traditional and AI"""
        
        # Calculate quality scores
        traditional_score = self._calculate_traditional_score(traditional)
        ai_score = self._calculate_ai_score(ai)
        
        print(f"Traditional score: {traditional_score:.2f}")
        print(f"AI score: {ai_score:.2f}")
        
        if traditional_score >= ai_score and traditional_score >= self.confidence_threshold:
            # Use traditional result
            return self._convert_traditional_result(traditional)
        elif ai_score >= self.confidence_threshold:
            # Use AI result
            return self._convert_ai_result(ai)
        else:
            # Both are low confidence, use traditional as fallback
            return self._convert_traditional_result(traditional, fallback=True)
    
    def _calculate_traditional_score(self, book: Any) -> float:
        """Calculate quality score for traditional detection"""
        if not book or book.numChapters < 2:
            return 0.0
        
        # Base score on number of chapters and heading quality
        base_score = min(book.numChapters / 10, 1.0)  # Normalize to 0-1
        
        # Check heading quality
        heading_quality = 0
        for heading_line in book.headings[:5]:  # Check first 5 headings
            heading_text = book.lines[heading_line]
            if any(keyword in heading_text.upper() for keyword in ['CHAPTER', 'PART', 'BOOK']):
                heading_quality += 0.2
        
        return min(base_score + heading_quality, 1.0)
    
    def _calculate_ai_score(self, result: ChapterDetectionResult) -> float:
        """Calculate quality score for AI detection"""
        if not result or not result.confidence_scores:
            return 0.0
        
        # Average confidence score
        avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
        
        # Penalize if too few or too many chapters
        chapter_count = len(result.chapters)
        if chapter_count < 2:
            return 0.0
        elif chapter_count > 50:
            avg_confidence *= 0.8  # Penalize too many chapters
        
        return avg_confidence
    
    def _convert_traditional_result(self, book: Any, fallback: bool = False) -> HybridResult:
        """Convert traditional chapterize result to HybridResult"""
        headings = [book.lines[i] for i in book.headings[:-1]]  # Exclude end location
        confidence = self._calculate_traditional_score(book)
        
        return HybridResult(
            chapters=book.chapters,
            headings=headings,
            confidence=confidence,
            method_used='traditional',
            fallback_used=fallback,
            metadata={
                'num_chapters': book.numChapters,
                'heading_locations': book.headings
            }
        )
    
    def _convert_ai_result(self, result: ChapterDetectionResult) -> HybridResult:
        """Convert AI detection result to HybridResult"""
        avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores) if result.confidence_scores else 0.0
        
        return HybridResult(
            chapters=result.chapters,
            headings=result.headings,
            confidence=avg_confidence,
            method_used=result.detection_method,
            fallback_used=False,
            metadata=result.metadata
        )
    
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
    """Example usage of hybrid detector"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hybrid Chapter Detection')
    parser.add_argument('book_path', help='Path to the book file (supports .txt and .epub formats)')
    parser.add_argument('--provider', default='bedrock', choices=['bedrock', 'openai', 'none'], 
                       help='LLM provider to use')
    parser.add_argument('--skip-ai', action='store_true', 
                       help='Skip AI detection and use only traditional method')
    parser.add_argument('--api-key', help='API key for OpenAI')
    parser.add_argument('--region', default='eu-central-1', help='AWS region for Bedrock')
    parser.add_argument('--profile', help='AWS profile for Bedrock')
    parser.add_argument('--confidence', type=float, default=0.7, help='Confidence threshold')
    
    args = parser.parse_args()
    
    detector = HybridChapterDetector(
        llm_provider=args.provider,
        api_key=args.api_key,
        region=args.region,
        profile=args.profile,
        confidence_threshold=args.confidence,
        skip_ai=args.skip_ai
    )
    
    result = detector.detect_chapters(args.book_path)
    
    print(f"\nHybrid Detection Results:")
    print(f"Chapters found: {len(result.chapters)}")
    print(f"Method used: {result.method_used}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Fallback used: {result.fallback_used}")
    print(f"Headings: {result.headings[:5]}...")

if __name__ == "__main__":
    main()
