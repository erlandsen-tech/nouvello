#!/usr/bin/env python3
"""
Simple wrapper script for chapter analysis
Easy-to-use command-line interface for analyzing EPUB chapters
"""

import sys
import os
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add ai directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai'))

from ai.chapter_analyzer import ChapterAnalyzer
from ai.epub_parser import EPUBParser


def parse_chapter_selection(chapter_spec, max_chapters):
    """
    Parse chapter selection string
    
    Examples:
        "0,1,2" -> [0, 1, 2]
        "0-5" -> [0, 1, 2, 3, 4, 5]
        "all" -> None (all chapters)
    """
    if not chapter_spec or chapter_spec.lower() == "all":
        return None
    
    if '-' in chapter_spec and ',' not in chapter_spec:
        # Range: 0-5
        try:
            start, end = chapter_spec.split('-')
            start, end = int(start.strip()), int(end.strip())
            return list(range(start, min(end + 1, max_chapters)))
        except ValueError:
            print(f"Error: Invalid range format '{chapter_spec}'")
            sys.exit(1)
    else:
        # List: 0,1,2 or mixed: 0-2,5,7-9
        indices = []
        for part in chapter_spec.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = part.split('-')
                    start, end = int(start.strip()), int(end.strip())
                    indices.extend(range(start, min(end + 1, max_chapters)))
                except ValueError:
                    print(f"Error: Invalid range format '{part}'")
                    sys.exit(1)
            else:
                try:
                    indices.append(int(part))
                except ValueError:
                    print(f"Error: Invalid chapter number '{part}'")
                    sys.exit(1)
        
        # Remove duplicates and sort
        return sorted(set(indices))


def list_chapters(epub_path):
    """List all chapters in an EPUB"""
    print(f"📚 Chapters in {os.path.basename(epub_path)}:")
    print("=" * 70)
    
    parser = EPUBParser(epub_path)
    chapters = parser.parse()
    
    if not chapters:
        print("No chapters found")
        return
    
    for i, chapter in enumerate(chapters):
        content_length = len(chapter.content)
        print(f"[{i:3d}] {chapter.title} ({content_length:,} characters)")
    
    print("\n" + "=" * 70)
    print(f"Total: {len(chapters)} chapters (EPUB)")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze EPUB chapters using AWS Bedrock",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all chapters
  %(prog)s book.epub

  # Analyze specific chapters
  %(prog)s book.epub -c 0,1,2
  %(prog)s book.epub --chapters 0-5

  # Mix ranges and individual chapters
  %(prog)s book.epub -c 0-2,5,8-10

  # List chapters without analyzing
  %(prog)s book.epub --list

  # Use specific AWS region
  %(prog)s book.epub --region us-west-2

  # Use specific output directory
  %(prog)s book.epub -o results/

  # Use specific model
  %(prog)s book.epub --model anthropic.claude-3-sonnet-20240229-v1:0
        """
    )
    
    parser.add_argument(
        'epub_file',
        help='Path to EPUB file to analyze'
    )
    
    parser.add_argument(
        '-c', '--chapters',
        default='all',
        help='Chapters to analyze: "all", "0,1,2", "0-5", or "0-2,5,8-10" (default: all)'
    )
    
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List all chapters and exit (no analysis)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='.',
        help='Output directory for results (default: current directory)'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['json', 'markdown', 'text', 'all'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--region',
        default=os.getenv('AWS_REGION', 'eu-central-1'),
        help='AWS region for Bedrock (default: from .env or eu-central-1)'
    )
    
    parser.add_argument(
        '--profile',
        default=os.getenv('AWS_PROFILE'),
        help='AWS profile to use (default: from .env)'
    )
    
    parser.add_argument(
        '--model',
        default=os.getenv('BEDROCK_MODEL'),
        help='Specific model to use (default: from .env)'
    )
    
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview selected chapters without analyzing'
    )
    
    parser.add_argument(
        '--style',
        help='Art style override for all images (e.g., "horror", "cute", "cyberpunk", "watercolor")'
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.epub_file):
        print(f"❌ Error: File not found: {args.epub_file}")
        sys.exit(1)
    
    # List chapters mode
    if args.list:
        list_chapters(args.epub_file)
        return
    
    # Parse EPUB
    print(f"📚 Parsing EPUB: {args.epub_file}")
    parser_obj = EPUBParser(args.epub_file)
    chapters = parser_obj.parse()
    
    if not chapters:
        print("❌ No chapters found in EPUB")
        sys.exit(1)
    
    print(f"✅ Found {len(chapters)} chapters")
    
    # Extract book metadata
    book_title = parser_obj.get_book_title()
    book_author = parser_obj.get_book_author()
    if book_title:
        print(f"📖 Book: {book_title}")
    if book_author:
        print(f"✍️  Author: {book_author}")
    
    # Parse chapter selection
    selected_indices = parse_chapter_selection(args.chapters, len(chapters))
    
    if selected_indices is None:
        print(f"🎯 Selected: All chapters ({len(chapters)} total)")
        chapters_to_analyze = chapters
    else:
        # Validate indices
        valid_indices = [i for i in selected_indices if 0 <= i < len(chapters)]
        if len(valid_indices) != len(selected_indices):
            invalid = [i for i in selected_indices if i < 0 or i >= len(chapters)]
            print(f"⚠️  Warning: Invalid chapter indices ignored: {invalid}")
        selected_indices = valid_indices
        
        print(f"🎯 Selected: {len(selected_indices)} chapters")
        chapters_to_analyze = [chapters[i] for i in selected_indices]
    
    # Preview mode
    if args.preview:
        print("\n📋 Preview of selected chapters:")
        print("=" * 70)
        for chapter in chapters_to_analyze:
            print(f"[{chapter.order}] {chapter.title}")
            print(f"    Length: {len(chapter.content):,} characters")
            print(f"    Preview: {chapter.content[:100]}...")
            print()
        return
    
    # Show what will be analyzed
    print("\n📋 Chapters to analyze:")
    for chapter in chapters_to_analyze[:10]:  # Show first 10
        print(f"  [{chapter.order}] {chapter.title}")
    if len(chapters_to_analyze) > 10:
        print(f"  ... and {len(chapters_to_analyze) - 10} more")
    
    # Confirm for large batch
    if len(chapters_to_analyze) > 10:
        print(f"\n⚠️  You are about to analyze {len(chapters_to_analyze)} chapters.")
        print("   This may take a while and will use AWS Bedrock credits.")
        response = input("   Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    # Initialize analyzer
    print(f"\n🚀 Initializing Bedrock analyzer...")
    print(f"   Region: {args.region}")
    if args.profile:
        print(f"   Profile: {args.profile}")
    if args.model:
        print(f"   Model: {args.model}")
    
    try:
        analyzer = ChapterAnalyzer(
            region=args.region,
            model=args.model,
            profile=args.profile
        )
    except Exception as e:
        print(f"\n❌ Error initializing analyzer: {e}")
        print("\n💡 Make sure:")
        print("   - AWS credentials are configured")
        print("   - You have Bedrock access enabled")
        print("   - boto3 is installed: pip install boto3")
        sys.exit(1)
    
    # Analyze chapters
    print(f"\n🔍 Analyzing chapters...")
    print("=" * 70)
    
    try:
        analyses = analyzer.analyze_chapters(chapters, selected_indices)
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    if not analyses:
        print("\n❌ No analyses generated")
        sys.exit(1)
    
    print("\n✅ Analysis complete!")
    
    # Infer art style from book content if no override specified
    inferred_style = None
    if not args.style and len(analyses) > 0:
        print(f"\n🎨 Inferring art style from book content...")
        try:
            # Import here to avoid circular dependency
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai'))
            from character_image_prompter import CharacterImagePrompter
            
            temp_prompter = CharacterImagePrompter(region=args.region, model=args.model, profile=args.profile)
            book_context = temp_prompter._extract_book_context(analyses)
            
            # Get the inferred style tags
            inferred_tags = book_context.get('art_style_tags', [])
            if inferred_tags:
                inferred_style = ', '.join(inferred_tags)
                print(f"   ✨ Detected style: {inferred_style}")
            
            # Also save other useful context
            detected_genre = book_context.get('genre', '')
            detected_mood = book_context.get('overall_mood', '')
            if detected_genre:
                print(f"   📚 Genre: {detected_genre}")
            if detected_mood:
                print(f"   🎭 Mood: {detected_mood}")
        except Exception as e:
            print(f"   ⚠️  Could not infer style: {e}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(args.epub_file))[0]
    
    # Export results
    print(f"\n💾 Exporting results to {args.output_dir}/...")
    
    formats_to_export = ['json', 'markdown', 'text'] if args.format == 'all' else [args.format]
    
    output_files = []
    for fmt in formats_to_export:
        ext = {'json': 'json', 'markdown': 'md', 'text': 'txt'}[fmt]
        output_path = os.path.join(args.output_dir, f"{base_name}_analysis.{ext}")
        
        # Add book metadata to the export
        if fmt == 'json':
            # Use override if provided, otherwise use inferred style
            final_style = args.style if args.style else inferred_style
            
            # Export with book metadata wrapper
            data = {
                'book_title': book_title,
                'book_author': book_author,
                'art_style': final_style,  # Save style (override or inferred)
                'chapters': [a.to_dict() for a in analyses]
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                import json as json_lib
                json_lib.dump(data, f, indent=2, ensure_ascii=False)
        else:
            analyzer.export_analyses(analyses, output_path, format=fmt)
        
        output_files.append(output_path)
        if len(formats_to_export) > 1:
            print(f"   ✅ {fmt.capitalize()}: {output_path}")
        else:
            print(f"   ✅ {output_path}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Chapters analyzed: {len(analyses)}")
    print(f"Total characters found: {sum(len(a.characters) for a in analyses)}")
    print(f"Total objects found: {sum(len(a.significant_objects) for a in analyses)}")
    print(f"\nOutput files: {len(output_files)}")
    for f in output_files:
        print(f"  • {f}")
    
    # Show first chapter preview
    if analyses:
        print("\n" + "=" * 70)
        print("📖 PREVIEW: First Chapter")
        print("=" * 70)
        first = analyses[0]
        print(f"Title: {first.chapter_title}")
        print(f"\nScene: {first.scene_description[:200]}...")
        print(f"\nMood: {first.mood_description[:200]}...")
        print(f"\nCharacters: {len(first.characters)} found")
        if first.characters:
            print(f"  First: {first.characters[0]['name']}")
        print(f"\nObjects: {len(first.significant_objects)} found")
        if first.significant_objects:
            print(f"  First: {first.significant_objects[0]['name']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)

