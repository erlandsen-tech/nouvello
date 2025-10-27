#!/usr/bin/env python3
"""
Demo script showing how to use the Chapter Analyzer with EPUB files
"""

from chapter_analyzer import ChapterAnalyzer, ChapterAnalysis
from epub_parser import EPUBParser
import json


def demo_basic_analysis():
    """Demo: Basic chapter analysis"""
    print("=" * 70)
    print("DEMO 1: Basic Chapter Analysis")
    print("=" * 70)
    
    # Initialize the analyzer
    analyzer = ChapterAnalyzer(
        provider="bedrock",
        region="us-east-1"
    )
    
    # Analyze first 2 chapters of Lovecraft
    epub_path = "../books/The_Complete_Works_of_H.P._Lovecraft.epub"
    
    print(f"\n📚 Analyzing first 2 chapters of: {epub_path}")
    analyses = analyzer.analyze_epub(epub_path, selected_chapters=[0, 1])
    
    # Print results
    for analysis in analyses:
        print("\n" + "=" * 70)
        print(f"📖 {analysis.chapter_title}")
        print("=" * 70)
        print(f"\n🎬 SCENE:")
        print(f"{analysis.scene_description}\n")
        print(f"🎭 MOOD:")
        print(f"{analysis.mood_description}\n")
        print(f"👥 CHARACTERS ({len(analysis.characters)}):")
        for char in analysis.characters:
            print(f"  • {char['name']}: {char['description'][:80]}...")
        print(f"\n🔮 SIGNIFICANT OBJECTS ({len(analysis.significant_objects)}):")
        for obj in analysis.significant_objects:
            print(f"  • {obj['name']}: {obj['description'][:80]}...")
        print(f"\n📝 SUMMARY:")
        print(f"{analysis.summary}\n")
    
    return analyses


def demo_selective_analysis():
    """Demo: Analyzing specific chapters"""
    print("\n" + "=" * 70)
    print("DEMO 2: Selective Chapter Analysis")
    print("=" * 70)
    
    # First, let's see what chapters are available
    epub_path = "../books/The_Complete_Works_of_H.P._Lovecraft.epub"
    parser = EPUBParser(epub_path)
    chapters = parser.parse()
    
    print(f"\n📚 Book has {len(chapters)} chapters:")
    for i, chapter in enumerate(chapters[:10]):  # Show first 10
        print(f"  [{i}] {chapter.title}")
    if len(chapters) > 10:
        print(f"  ... and {len(chapters) - 10} more")
    
    # User can choose which chapters to analyze
    print("\n🎯 Analyzing chapters [0, 2, 5]...")
    
    analyzer = ChapterAnalyzer(provider="bedrock", region="us-east-1")
    analyses = analyzer.analyze_chapters(chapters, selected_indices=[0, 2, 5])
    
    print(f"\n✅ Analyzed {len(analyses)} chapters")
    for analysis in analyses:
        print(f"  • Chapter {analysis.chapter_number}: {analysis.chapter_title}")


def demo_export_formats():
    """Demo: Exporting in different formats"""
    print("\n" + "=" * 70)
    print("DEMO 3: Export Formats")
    print("=" * 70)
    
    analyzer = ChapterAnalyzer(provider="bedrock", region="us-east-1")
    
    # Analyze one chapter
    epub_path = "../books/The_Complete_Works_of_H.P._Lovecraft.epub"
    analyses = analyzer.analyze_epub(epub_path, selected_chapters=[0])
    
    if analyses:
        print("\n💾 Exporting in different formats...")
        
        # JSON format
        analyzer.export_analyses(analyses, "demo_output.json", format="json")
        print("  ✅ JSON: demo_output.json")
        
        # Markdown format
        analyzer.export_analyses(analyses, "demo_output.md", format="markdown")
        print("  ✅ Markdown: demo_output.md")
        
        # Text format
        analyzer.export_analyses(analyses, "demo_output.txt", format="text")
        print("  ✅ Text: demo_output.txt")
        
        # Show JSON structure
        print("\n📋 JSON Structure Preview:")
        print(json.dumps(analyses[0].to_dict(), indent=2)[:500] + "...")


def demo_programmatic_access():
    """Demo: Using analysis data programmatically"""
    print("\n" + "=" * 70)
    print("DEMO 4: Programmatic Access to Analysis Data")
    print("=" * 70)
    
    analyzer = ChapterAnalyzer(provider="bedrock", region="us-east-1")
    
    # Analyze chapters
    epub_path = "../books/The_Complete_Works_of_H.P._Lovecraft.epub"
    analyses = analyzer.analyze_epub(epub_path, selected_chapters=[0, 1])
    
    # Example: Extract all character names
    print("\n👥 All Characters Found:")
    all_characters = set()
    for analysis in analyses:
        for char in analysis.characters:
            all_characters.add(char['name'])
    for name in sorted(all_characters):
        print(f"  • {name}")
    
    # Example: Extract all moods
    print("\n🎭 Mood Progression:")
    for analysis in analyses:
        mood_summary = analysis.mood_description.split('.')[0]  # First sentence
        print(f"  Chapter {analysis.chapter_number}: {mood_summary}")
    
    # Example: Find chapters with specific objects
    print("\n🔍 Chapters with 'book' or 'manuscript':")
    for analysis in analyses:
        for obj in analysis.significant_objects:
            obj_name = obj['name'].lower()
            if 'book' in obj_name or 'manuscript' in obj_name:
                print(f"  • {analysis.chapter_title}: {obj['name']}")


def interactive_mode():
    """Interactive chapter selection"""
    print("\n" + "=" * 70)
    print("INTERACTIVE MODE")
    print("=" * 70)
    
    epub_path = "../books/The_Complete_Works_of_H.P._Lovecraft.epub"
    
    # Parse and show chapters
    parser = EPUBParser(epub_path)
    chapters = parser.parse()
    
    print(f"\n📚 Found {len(chapters)} chapters in the book:\n")
    for i, chapter in enumerate(chapters[:20]):  # Show first 20
        print(f"  [{i:2d}] {chapter.title}")
    if len(chapters) > 20:
        print(f"  ... and {len(chapters) - 20} more")
    
    print("\n" + "=" * 70)
    print("Examples of how to analyze:")
    print("  analyzer.analyze_epub(epub_path, selected_chapters=[0, 1, 2])")
    print("  analyzer.analyze_epub(epub_path, selected_chapters=list(range(0, 5)))")
    print("  analyzer.analyze_epub(epub_path)  # All chapters")
    print("=" * 70)


def main():
    """Run all demos"""
    import sys
    
    print("\n🎬 Chapter Analyzer Demo")
    print("=" * 70)
    print("This demo shows how to use the Chapter Analyzer to extract:")
    print("  1. Scene descriptions")
    print("  2. Mood/atmosphere")
    print("  3. Character descriptions")
    print("  4. Significant objects")
    print("  5. Chapter summaries")
    print("=" * 70)
    
    # Check if EPUB file exists
    import os
    epub_path = "../books/The_Complete_Works_of_H.P._Lovecraft.epub"
    if not os.path.exists(epub_path):
        print(f"\n⚠️  EPUB file not found: {epub_path}")
        print("Please provide a valid EPUB file path")
        return
    
    demos = [
        ("1", "Basic Analysis", demo_basic_analysis),
        ("2", "Selective Analysis", demo_selective_analysis),
        ("3", "Export Formats", demo_export_formats),
        ("4", "Programmatic Access", demo_programmatic_access),
        ("5", "Interactive Mode", interactive_mode),
    ]
    
    if len(sys.argv) > 1:
        # Run specific demo
        demo_num = sys.argv[1]
        for num, name, func in demos:
            if num == demo_num:
                print(f"\n🎯 Running: {name}")
                func()
                return
        print(f"Unknown demo: {demo_num}")
    else:
        # Show menu
        print("\nAvailable demos:")
        for num, name, _ in demos:
            print(f"  {num}. {name}")
        print("\nUsage: python demo_chapter_analysis.py <demo_number>")
        print("Example: python demo_chapter_analysis.py 1")
        print("\nOr run all demos:")
        print("  python demo_chapter_analysis.py all")
        
        if len(sys.argv) == 1 or sys.argv[1] == "all":
            print("\n" + "=" * 70)
            print("Running ALL demos...")
            print("=" * 70)
            for num, name, func in demos:
                try:
                    func()
                except KeyboardInterrupt:
                    print("\n\n⚠️  Demo interrupted by user")
                    break
                except Exception as e:
                    print(f"\n❌ Error in {name}: {e}")
                    import traceback
                    traceback.print_exc()


if __name__ == "__main__":
    main()

