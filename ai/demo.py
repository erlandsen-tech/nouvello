"""
Simple demo script for AI-powered chapter detection
For comprehensive testing, use: ai/test_chapter_detection.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.hybrid_chapter_detector import HybridChapterDetector
import time


def demo_chapter_detection(book_path: str = "books/alice.txt"):
    """Quick demo of chapter detection"""
    print("🤖 AI-Powered Chapter Detection Demo")
    print("=" * 50)
    
    if not os.path.exists(book_path):
        print(f"⚠️  Book not found: {book_path}")
        print("Try: python ai/demo.py books/your_book.txt")
        return
    
    detector = HybridChapterDetector()
    
    print(f"\n📚 Analyzing: {os.path.basename(book_path)}")
    print("-" * 30)
    
    start_time = time.time()
    result = detector.detect_chapters(book_path)
    elapsed = time.time() - start_time
    
    print(f"✅ Chapters found: {len(result.chapters)}")
    print(f"🎯 Method: {result.method_used}")
    print(f"📊 Confidence: {result.confidence:.2f}")
    print(f"⏱️  Time: {elapsed:.2f}s")
    
    if result.headings:
        print(f"\n📝 Sample headings:")
        for i, heading in enumerate(result.headings[:5], 1):
            print(f"   {i}. {heading}")
    
    print(f"\n💡 For comprehensive testing:")
    print(f"   python ai/test_chapter_detection.py {book_path}")


def main():
    """Run demo"""
    import sys
    
    book_path = sys.argv[1] if len(sys.argv) > 1 else "books/alice.txt"
    demo_chapter_detection(book_path)


if __name__ == "__main__":
    main()
