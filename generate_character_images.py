#!/usr/bin/env python3
"""
Complete workflow: Analyze chapters → Generate character prompts → Generate images
"""

import sys
import os
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add ai directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai'))

from ai.chapter_analyzer import ChapterAnalyzer, ChapterAnalysis
from ai.character_image_prompter import CharacterImagePrompter
from ai.gemini_image_generator import GeminiImageGenerator, GENAI_AVAILABLE
from ai.expression_prompter import ExpressionPrompter
from ai.epub_parser import EPUBParser
import json
import re


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename"""
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace spaces and multiple underscores
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def _export_chapter_structure(analyses, chapters_dir, epub_chapters, selected_indices):
    """Export individual chapter directories with content and analysis"""
    chapters_to_export = epub_chapters if selected_indices is None else [epub_chapters[i] for i in selected_indices]
    
    for analysis, chapter in zip(analyses, chapters_to_export):
        # Create chapter directory: "01_Chapter_Title"
        chapter_num = f"{analysis.chapter_number:02d}"
        safe_title = _sanitize_filename(analysis.chapter_title)
        chapter_dirname = f"{chapter_num}_{safe_title}"
        chapter_path = os.path.join(chapters_dir, chapter_dirname)
        os.makedirs(chapter_path, exist_ok=True)
        
        # Export chapter content
        content_file = os.path.join(chapter_path, "content.txt")
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(f"Chapter {analysis.chapter_number}: {analysis.chapter_title}\n")
            f.write("=" * 80 + "\n\n")
            f.write(chapter.content)
        
        # Export chapter-specific analysis
        analysis_file = os.path.join(chapter_path, "analysis.json")
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis.to_dict(), f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Complete workflow: Analyze EPUB and generate character images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Complete Workflow:
  1. Analyze EPUB chapters (or load existing analysis)
  2. Generate character image prompts
  3. Generate images using Gemini API

Examples:
  # Full workflow from EPUB
  %(prog)s book.epub --gemini-key YOUR_KEY

  # Use existing analysis
  %(prog)s --analysis book_analysis.json --gemini-key YOUR_KEY

  # Skip image generation (only create prompts)
  %(prog)s book.epub --skip-images

  # Custom output directory
  %(prog)s book.epub -o results/ --gemini-key YOUR_KEY

Environment Variables:
  GEMINI_API_KEY - Your Gemini API key (avoids --gemini-key)
  AWS_PROFILE - AWS profile for Bedrock (if analyzing chapters)
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        'epub_file',
        nargs='?',
        help='Path to EPUB file to analyze'
    )
    input_group.add_argument(
        '--analysis',
        help='Path to existing analysis JSON file (skip chapter analysis)'
    )
    
    # Chapter selection
    parser.add_argument(
        '-c', '--chapters',
        default='all',
        help='Chapters to analyze: "all", "0,1,2", "0-5" (default: all). Ignored if using --analysis.'
    )
    
    # Output options
    parser.add_argument(
        '-o', '--output-dir',
        default='output',
        help='Output directory for all results (default: output)'
    )
    
    # Bedrock options (for chapter analysis)
    parser.add_argument(
        '--bedrock-region',
        default=os.getenv('AWS_REGION', 'eu-central-1'),
        help='AWS region for Bedrock (default: from .env or eu-central-1)'
    )
    
    parser.add_argument(
        '--bedrock-profile',
        default=os.getenv('AWS_PROFILE'),
        help='AWS profile for Bedrock (default: from .env)'
    )
    
    parser.add_argument(
        '--bedrock-model',
        default=os.getenv('BEDROCK_MODEL'),
        help='Specific Bedrock model to use (default: from .env)'
    )
    
    # Gemini options (for image generation)
    parser.add_argument(
        '--gemini-key',
        default=os.getenv('GEMINI_API_KEY'),
        help='Gemini API key (default: from .env or GEMINI_API_KEY env var)'
    )
    
    parser.add_argument(
        '--gemini-model',
        default=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-image'),
        help='Gemini model for images (default: from .env or gemini-2.5-flash-image)'
    )
    
    parser.add_argument(
        '--aspect-ratio',
        default='1:1',
        choices=['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'],
        help='Aspect ratio for generated images (default: 1:1)'
    )
    
    # Workflow control
    parser.add_argument(
        '--skip-images',
        action='store_true',
        help='Skip image generation (only generate prompts)'
    )
    
    parser.add_argument(
        '--skip-expressions',
        action='store_true',
        help='Skip expression prompt generation (default unless GENERATE_EXPRESSIONS=true)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between Gemini API calls in seconds (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    # Validate Gemini API key if needed
    if not args.skip_images and not GENAI_AVAILABLE:
        print("❌ Error: google-genai not installed")
        print("   Install with: pip install google-genai")
        sys.exit(1)
    
    if not args.skip_images:
        gemini_key = args.gemini_key
        if not gemini_key:
            print("❌ Error: Gemini API key required for image generation")
            print("   Set GEMINI_API_KEY environment variable or use --gemini-key")
            sys.exit(1)
    
    # Determine base name for files
    if args.analysis:
        base_name = os.path.splitext(os.path.basename(args.analysis))[0]
        base_name = base_name.replace("_analysis", "")
    else:
        base_name = os.path.splitext(os.path.basename(args.epub_file))[0]
    
    # Create book directory structure
    book_dir = os.path.join(args.output_dir, base_name)
    os.makedirs(book_dir, exist_ok=True)
    
    # File paths
    analysis_file = os.path.join(book_dir, "analysis.json")
    prompts_file = os.path.join(book_dir, "character_prompts.json")
    images_dir = os.path.join(book_dir, "images")
    chapters_dir = os.path.join(book_dir, "chapters")
    expressions_dir = os.path.join(book_dir, "prompts")
    
    print("=" * 70)
    print("🎨 CHARACTER IMAGE GENERATION WORKFLOW")
    print("=" * 70)
    print(f"Book: {base_name}")
    print(f"Output: {book_dir}/")
    
    # STEP 1: Chapter Analysis (or load existing)
    epub_chapters = None  # Will be None if loading from existing analysis
    
    if args.analysis:
        print("\n📖 STEP 1: Loading existing analysis")
        print(f"   File: {args.analysis}")
        if not os.path.exists(args.analysis):
            print(f"❌ Error: Analysis file not found: {args.analysis}")
            sys.exit(1)
        # Copy to output directory if not already there
        if os.path.abspath(args.analysis) != os.path.abspath(analysis_file):
            import shutil
            shutil.copy(args.analysis, analysis_file)
            print(f"   ✅ Copied to: {analysis_file}")
        print(f"   ℹ️  Note: Chapter content not available (loaded from existing analysis)")
    else:
        print("\n📖 STEP 1: Analyzing EPUB chapters")
        print(f"   File: {args.epub_file}")
        
        if not os.path.exists(args.epub_file):
            print(f"❌ Error: EPUB file not found: {args.epub_file}")
            sys.exit(1)
        
        # Parse EPUB
        parser_obj = EPUBParser(args.epub_file)
        epub_chapters = parser_obj.parse()
        
        if not epub_chapters:
            print("❌ No chapters found in EPUB")
            sys.exit(1)
        
        print(f"   ✅ Found {len(epub_chapters)} chapters")
        
        # Parse chapter selection
        if args.chapters and args.chapters.lower() != "all":
            from analyze_chapters import parse_chapter_selection
            selected_indices = parse_chapter_selection(args.chapters, len(epub_chapters))
            print(f"   🎯 Selected: {len(selected_indices)} chapters")
        else:
            selected_indices = None
            print(f"   🎯 Selected: All chapters")
        
        # Initialize analyzer
        print(f"\n   🚀 Initializing analyzer...")
        try:
            analyzer = ChapterAnalyzer(
                region=args.bedrock_region,
                model=args.bedrock_model,
                profile=args.bedrock_profile
            )
        except Exception as e:
            print(f"\n❌ Error initializing analyzer: {e}")
            sys.exit(1)
        
        # Analyze
        print(f"\n   🔍 Analyzing chapters...")
        try:
            analyses = analyzer.analyze_chapters(epub_chapters, selected_indices)
        except Exception as e:
            print(f"\n❌ Error during analysis: {e}")
            sys.exit(1)
        
        if not analyses:
            print("❌ No analyses generated")
            sys.exit(1)
        
        # Export analysis
        analyzer.export_analyses(analyses, analysis_file, format="json")
        
        # Export individual chapters (only if we have the EPUB content)
        if epub_chapters is not None:
            os.makedirs(chapters_dir, exist_ok=True)
            _export_chapter_structure(analyses, chapters_dir, epub_chapters, selected_indices)
            print(f"   ✅ Chapters exported: {chapters_dir}/")
        
        print(f"   ✅ Analysis saved: {analysis_file}")
    
    # STEP 2: Generate character prompts
    print("\n🎨 STEP 2: Generating character image prompts")
    print(f"   Input: {analysis_file}")
    
    expressions_generated = False
    
    try:
        # Build a set of existing character images to skip prompt generation
        existing_images = set()
        if os.path.isdir(images_dir):
            for fname in os.listdir(images_dir):
                if fname.lower().endswith('.png'):
                    existing_images.add(os.path.splitext(fname)[0].lower())
        
        # Check if prompts file already exists
        if os.path.exists(prompts_file):
            print(f"   ℹ️  Loading existing prompts from: {prompts_file}")
            # Load existing prompts instead of regenerating
            from ai.character_image_prompter import CharacterImagePrompt
            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts_data = json.load(f)
            prompts = [CharacterImagePrompt.from_dict(p) for p in prompts_data]
            print(f"   ✅ Loaded {len(prompts)} existing character prompts")
        else:
            # Generate new prompts
            print(f"   🔄 Generating new character prompts...")
            prompter = CharacterImagePrompter(
                region=args.bedrock_region,
                model=args.bedrock_model,
                profile=args.bedrock_profile
            )
            prompts = prompter.generate_from_analysis_file(analysis_file)
            
            # Export prompts for future use
            prompter.export_prompts(prompts, prompts_file, format="json")
            print(f"   ✅ Generated prompts for {len(prompts)} characters")
            print(f"   ✅ Output: {prompts_file}")
        if existing_images:
            filtered = []
            for p in prompts:
                basename = p.character_name.lower().replace(' ', '_')
                if basename in existing_images:
                    print(f"   ⏭️  Skipping prompt for {p.character_name} (image exists)")
                    continue
                filtered.append(p)
            prompts = filtered
        
        if not prompts:
            print("✅ All character images already exist - nothing to generate")
            print(f"   📁 Output: {images_dir}")
            # Exit successfully - this is a valid state (already complete)
            print("\n" + "=" * 70)
            print("✅ WORKFLOW COMPLETE!")
            print("=" * 70)
            print(f"\nAll character images already exist in: {images_dir}")
            sys.exit(0)
        
        # STEP 2.5: Generate expression prompts (opt-in via env or explicit flag)
        generate_expressions_env = os.getenv('GENERATE_EXPRESSIONS', 'false').lower() == 'true'
        want_expressions = (not args.skip_expressions) and generate_expressions_env

        if want_expressions:
            print("\n🎭 STEP 2.5: Generating expression variation prompts")
            try:
                expr_prompter = ExpressionPrompter()
                all_expressions = expr_prompter.generate_from_character_prompts_file(
                    prompts_file,
                    expressions_dir
                )
                expressions_generated = True
                print(f"   ✅ Generated {len(all_expressions)} character expression sets")
                print(f"   ✅ Output: {expressions_dir}/")
            except Exception as e:
                print(f"   ⚠️  Warning: Failed to generate expressions: {e}")
        else:
            reason = "GENERATE_EXPRESSIONS!=true" if not generate_expressions_env else "--skip-expressions"
            print(f"\n⏩ STEP 2.5: Skipping expression prompts ({reason})")
        
    except Exception as e:
        print(f"❌ Error generating prompts: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # STEP 3: Generate images
    if args.skip_images:
        print("\n⏩ STEP 3: Skipping image generation (--skip-images)")
        print("\n✅ Workflow complete! Prompts are ready for manual image generation.")
    else:
        print("\n🖼️  STEP 3: Generating images with Gemini API")
        print(f"   Input: {prompts_file}")
        print(f"   Output: {images_dir}")
        print(f"   Model: {args.gemini_model}")
        print(f"   Aspect ratio: {args.aspect_ratio}")
        
        try:
            generator = GeminiImageGenerator(
                api_key=gemini_key,
                model=args.gemini_model
            )
            
            results = generator.generate_from_prompts_file(
                prompts_file,
                images_dir,
                aspect_ratio=args.aspect_ratio,
                delay_seconds=args.delay
            )
            
            # Export report
            report_path = os.path.join(images_dir, "generation_report.json")
            generator.export_generation_report(results, report_path)
            
            # Summary
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            
            print(f"\n   ✅ Generated {successful} images")
            if failed > 0:
                print(f"   ⚠️  Failed: {failed}")
            
        except Exception as e:
            print(f"❌ Error generating images: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ WORKFLOW COMPLETE!")
    print("=" * 70)
    print(f"\nBook directory: {book_dir}/")
    print(f"\nStructure:")
    print(f"  📁 {base_name}/")
    print(f"     ├── 📄 analysis.json")
    print(f"     ├── 📝 character_prompts.json")
    if epub_chapters is not None:
        print(f"     ├── 📁 chapters/")
        print(f"     │   ├── 01_Chapter_Name/")
        print(f"     │   │   ├── content.txt")
        print(f"     │   │   └── analysis.json")
        print(f"     │   └── ...")
    if expressions_generated:
        print(f"     ├── 📁 prompts/")
        print(f"     │   ├── all_expressions.json")
        print(f"     │   ├── Character_1/expressions.json")
        print(f"     │   └── ...")
    if not args.skip_images:
        print(f"     └── 📁 images/")
        print(f"         ├── Character1.png")
        print(f"         ├── Character2.png")
        print(f"         └── generation_report.json")
    else:
        if epub_chapters is not None or expressions_generated:
            print(f"     └── 📁 images/ (not generated)")
        else:
            print(f"     └── (no images generated)")
    
    notes = []
    if epub_chapters is not None:
        notes.append(f"Chapter content included (analyzed from EPUB)")
    if expressions_generated:
        notes.append(f"Expression prompts generated for VN use")
    if notes:
        print(f"\nNotes: {' | '.join(notes)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)

