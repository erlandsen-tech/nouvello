#!/usr/bin/env python3
"""
Complete Book to Visual Novel Pipeline
From EPUB to React app with character consistency
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import argparse

# Add the ai directory to the path
sys.path.insert(0, str(Path(__file__).parent / "ai"))

from ai.epub_parser import EPUBParser


class BookToVNConverter:
    """Complete pipeline from EPUB to React visual novel"""
    
    def __init__(self, epub_path: str, output_base: str = "output", art_style: Optional[str] = None):
        self.epub_path = Path(epub_path)
        self.output_base = Path(output_base)
        self.book_name = self.epub_path.stem.lower().replace(' ', '_')
        self.book_dir = self.output_base / self.book_name
        self.art_style = art_style  # Optional style override for the entire book
        
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")
    
    def run_complete_pipeline(self, selected_chapters: Optional[List[int]] = None, resume_from: Optional[str] = None):
        """Run the complete pipeline from EPUB to React app"""
        print("=" * 80)
        print("📚 COMPLETE BOOK TO VISUAL NOVEL PIPELINE")
        print("=" * 80)
        print(f"📖 Book: {self.epub_path.name}")
        print(f"📁 Output: {self.book_dir}")
        if resume_from:
            print(f"🔄 Resuming from step: {resume_from}")
        print()
        
        # Define pipeline steps
        steps = {
            'parse': ('Parse EPUB and select chapters', self._parse_and_select_chapters),
            'analyze': ('Analyze selected chapters', self._analyze_chapters),
            'characters': ('Generate character images', self._generate_characters),
            'scenes': ('Generate scene segmentation', self._generate_scenes),
            'structure': ('Create chapter structure', self._create_chapter_structure),
            'consistent': ('Generate consistent scene images', self._generate_consistent_scenes),
            'copy': ('Copy to React app', self._copy_to_react_app),
            'update': ('Update React app book list', self._update_react_book_list)
        }
        
        # Determine where to start
        start_step = resume_from if resume_from else 'parse'
        step_names = list(steps.keys())
        
        if start_step not in step_names:
            print(f"❌ Invalid resume step: {start_step}")
            print(f"Available steps: {', '.join(step_names)}")
            return
        
        start_index = step_names.index(start_step)
        
        # Run pipeline steps
        chapters = None
        for i, (step_name, (step_desc, step_func)) in enumerate(steps.items()):
            if i < start_index:
                continue
                
            print(f"\n{'='*20} STEP {i+1}: {step_desc.upper()} {'='*20}")
            print("-" * 50)
            
            try:
                if step_name == 'parse':
                    chapters = step_func(selected_chapters)
                elif step_name == 'analyze':
                    # For analyze step, use chapters if available, or selected_chapters if it's a list
                    if chapters:
                        step_func(chapters)
                    elif selected_chapters and isinstance(selected_chapters, list):
                        step_func(selected_chapters)
                    else:
                        print("⚠️  Skipping analyze step - no chapters available")
                        print("   Run from 'parse' step to select chapters first")
                elif step_name == 'characters':
                    # For characters step, use chapters if available, or selected_chapters if it's a list
                    if chapters:
                        step_func(chapters)
                    elif selected_chapters and isinstance(selected_chapters, list):
                        step_func(selected_chapters)
                    else:
                        print("⚠️  Skipping characters step - no chapters available")
                        print("   Run from 'parse' step to select chapters first")
                else:
                    step_func()
                print(f"✅ {step_desc} complete")
            except Exception as e:
                print(f"❌ Error in {step_desc}: {e}")
                print(f"\n🔄 To resume from this step, run:")
                print(f"   python book_to_vn.py {self.epub_path} --resume-from {step_name}")
                raise
        
        print("\n" + "=" * 80)
        print("🎉 PIPELINE COMPLETE!")
        print("=" * 80)
        print(f"✅ Book ready: {self.book_name}")
        print(f"📱 React app: http://localhost:3000")
        print(f"📁 Book data: {self.book_dir}")
        print("=" * 80)
    
    def _parse_and_select_chapters(self, selected_chapters: Optional[List[int]] = None) -> List[int]:
        """Parse EPUB and let user select chapters"""
        print("📖 STEP 1: Parsing EPUB and selecting chapters")
        print("-" * 50)
        
        parser = EPUBParser(str(self.epub_path))
        chapters = parser.parse()
        
        print(f"✅ Found {len(chapters)} chapters:")
        story_chapters = []
        for i, chapter in enumerate(chapters, 1):
            title = chapter.title if hasattr(chapter, 'title') else f'Chapter {i}'
            # Detect story chapters (contain "Chapter" or are numbered)
            is_story = ("Chapter" in title or "CHAPTER" in title) and "Contents" not in title and "License" not in title
            if is_story:
                story_chapters.append(i)
                print(f"  [{i:2d}] {title} ⭐ (Story)")
            else:
                print(f"  [{i:2d}] {title}")
        
        # Auto-suggest story chapters
        if story_chapters:
            print(f"\n💡 Story chapters detected: {story_chapters}")
            print(f"   First story chapter: {story_chapters[0]}")
            print(f"   All story chapters: {story_chapters}")
        
        if selected_chapters is None:
            print("\n🎯 Select chapters to convert:")
            print("  • Enter chapter numbers separated by commas (e.g., 1,3,5)")
            print("  • Enter 'all' to select all chapters")
            print("  • Enter 'first' to select just the first chapter")
            if story_chapters:
                print(f"  • Enter 'story' to select story chapters only ({story_chapters})")
                print(f"  • Enter 'demo' to select first story chapter ({story_chapters[0]})")
            
            while True:
                choice = input("\nYour selection: ").strip().lower()
                
                if choice == 'all':
                    selected_chapters = list(range(1, len(chapters) + 1))
                    break
                elif choice == 'first':
                    selected_chapters = [1]
                    break
                elif choice == 'story' and story_chapters:
                    selected_chapters = story_chapters
                    break
                elif choice == 'demo' and story_chapters:
                    selected_chapters = [story_chapters[0]]
                    break
                else:
                    try:
                        selected_chapters = [int(x.strip()) for x in choice.split(',')]
                        # Validate chapter numbers
                        valid_chapters = [c for c in selected_chapters if 1 <= c <= len(chapters)]
                        if len(valid_chapters) != len(selected_chapters):
                            print("❌ Some chapter numbers are invalid. Please try again.")
                            continue
                        selected_chapters = valid_chapters
                        break
                    except ValueError:
                        print("❌ Invalid input. Please enter numbers separated by commas.")
                        continue
        elif isinstance(selected_chapters, str):
            # Handle string keywords passed from command line
            if selected_chapters == 'all':
                selected_chapters = list(range(1, len(chapters) + 1))
            elif selected_chapters == 'first':
                selected_chapters = [1]
            elif selected_chapters == 'story' and story_chapters:
                selected_chapters = story_chapters
            elif selected_chapters == 'demo' and story_chapters:
                selected_chapters = [story_chapters[0]]
            else:
                print(f"❌ Unknown keyword: {selected_chapters}")
                sys.exit(1)
        
        print(f"\n✅ Selected chapters: {selected_chapters}")
        return selected_chapters
    
    def _analyze_chapters(self, selected_chapters: List[int]):
        """Analyze selected chapters"""
        print(f"\n🔍 STEP 2: Analyzing {len(selected_chapters)} selected chapters")
        print("-" * 50)
        
        # Check if analysis already exists
        analysis_dest = self.book_dir / "analysis.json"
        if analysis_dest.exists():
            print(f"✅ Chapter analysis already exists: {analysis_dest}")
            print(f"   ⏭️  Skipping chapter analysis (file already exists)")
            print(f"\n💡 To re-analyze chapters, delete {analysis_dest} and run again")
            return
        
        # Create chapter list string for the analyzer
        chapter_list = ','.join(map(str, selected_chapters))
        
        # Get model from env (or use default)
        analysis_model = os.getenv("ANALYSIS_MODEL", os.getenv("BEDROCK_MODEL"))
        
        cmd = [
            "python", "analyze_chapters.py",
            str(self.epub_path),
            "-c", chapter_list,
            "-o", str(self.output_base)
        ]
        
        # Add model flag if specified
        if analysis_model:
            cmd.extend(["--bedrock-model", analysis_model])
        
        # Add style override if specified
        if self.art_style:
            cmd.extend(["--style", self.art_style])
        
        try:
            subprocess.run(cmd, check=True)
            
            # Ensure book directory exists
            self.book_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy analysis file to book directory with correct name
            analysis_source = self.output_base / f"{self.book_name}_analysis.json"
            analysis_dest = self.book_dir / "analysis.json"
            
            if analysis_source.exists():
                shutil.copy2(analysis_source, analysis_dest)
                print(f"✅ Copied analysis to: {analysis_dest}")
            else:
                print(f"⚠️  Warning: Analysis file not found at {analysis_source}")
            
            print("✅ Chapter analysis complete")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error analyzing chapters: {e}")
            raise
    
    def _generate_characters(self, selected_chapters: List[int]):
        """Generate character images"""
        print(f"\n🎨 STEP 3: Generating character images")
        print("-" * 50)
        
        # Copy analysis file to the correct location for generate_character_images.py
        analysis_source = self.book_dir / "analysis.json"
        analysis_temp = self.output_base / f"{self.book_name}_analysis.json"
        
        if analysis_source.exists():
            shutil.copy2(analysis_source, analysis_temp)
            print(f"✅ Copied analysis to: {analysis_temp}")
        
        # Get model from env (or use default)
        character_model = os.getenv("CHARACTER_MODEL", os.getenv("BEDROCK_MODEL"))
        
        cmd = [
            "python", "generate_character_images.py",
            "--analysis", str(analysis_temp),
            "-o", str(self.output_base)
        ]
        
        # Add model flag if specified
        if character_model:
            cmd.extend(["--bedrock-model", character_model])
        
        try:
            subprocess.run(cmd, check=True)
            print("✅ Character images generated")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generating characters: {e}")
            raise
    
    def _generate_scenes(self):
        """Generate scene segmentation"""
        print(f"\n🎬 STEP 4: Generating scene segmentation")
        print("-" * 50)
        
        # Get model from env (or use default)
        scene_model = os.getenv("SCENE_MODEL", os.getenv("BEDROCK_MODEL"))
        
        # Get parallelization settings
        chapter_workers = os.getenv("CHAPTER_SEG_WORKERS", "3")  # Default to 3 for better throughput
        
        cmd = [
            "python", "ai/scene_segmentation.py",
            str(self.book_dir),
            str(self.book_dir),
            "--windowed",  # Enable parallel windowed segmentation
            "--chapter-workers", chapter_workers  # Enable parallel chapter processing
        ]
        
        # Add model flag if specified
        if scene_model:
            cmd.extend(["--model", scene_model])
        
        try:
            subprocess.run(cmd, check=True)
            print("✅ Scene segmentation complete")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generating scenes: {e}")
            raise
    
    def _create_chapter_structure(self):
        """Create per-chapter directory structure from scenes.json"""
        print(f"\n📂 STEP 4.5: Creating chapter directory structure")
        print("-" * 50)
        
        scenes_file = self.book_dir / "scenes.json"
        analysis_file = self.book_dir / "analysis.json"
        chapters_dir = self.book_dir / "chapters"
        
        if not scenes_file.exists():
            print(f"⚠️  No scenes.json found, skipping chapter structure creation")
            return
        
        if not analysis_file.exists():
            print(f"⚠️  No analysis.json found, skipping chapter structure creation")
            return
        
        # Load scenes and analysis
        with open(scenes_file, 'r') as f:
            all_scenes = json.load(f)
        
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
        
        # Handle both old format (array) and new format (object with book_title)
        if isinstance(analysis_data, dict) and 'chapters' in analysis_data:
            chapters_list = analysis_data['chapters']
        else:
            chapters_list = analysis_data
        
        # Group scenes by chapter
        scenes_by_chapter = {}
        for scene in all_scenes:
            chapter_num = scene.get('chapter_number', 0)
            if chapter_num not in scenes_by_chapter:
                scenes_by_chapter[chapter_num] = []
            scenes_by_chapter[chapter_num].append(scene)
        
        # Create chapter directories
        chapters_dir.mkdir(exist_ok=True)
        
        for chapter in chapters_list:
            chapter_num = chapter.get('chapter_number', 0)
            chapter_title = chapter.get('chapter_title', f'Chapter {chapter_num}')
            
            # Create sanitized directory name
            safe_title = chapter_title.replace(' ', '_').replace('/', '_').replace('\\', '_')
            safe_title = ''.join(c for c in safe_title if c.isalnum() or c in ('_', '-'))
            chapter_dirname = f"{chapter_num:02d}_{safe_title}"
            
            chapter_path = chapters_dir / chapter_dirname
            chapter_path.mkdir(exist_ok=True)
            
            # Copy chapter analysis
            chapter_analysis_file = chapter_path / "analysis.json"
            with open(chapter_analysis_file, 'w') as f:
                json.dump(chapter, f, indent=2)
            
            # Save chapter scenes
            chapter_scenes = scenes_by_chapter.get(chapter_num, [])
            if chapter_scenes:
                chapter_scenes_file = chapter_path / "scenes.json"
                with open(chapter_scenes_file, 'w') as f:
                    json.dump(chapter_scenes, f, indent=2)
                print(f"  ✅ Created: {chapter_dirname}/ ({len(chapter_scenes)} scenes)")
            else:
                print(f"  ⚠️  No scenes found for: {chapter_dirname}/")
        
        print(f"✅ Chapter structure created in: {chapters_dir}")
    
    def _generate_consistent_scenes(self):
        """Generate consistent scene images"""
        print(f"\n🎭 STEP 5: Generating consistent scene images")
        print("-" * 50)
        
        # Find the correct character images directory
        character_dir = self.book_dir / "images"
        if not character_dir.exists():
            # Try alternative locations
            possible_dirs = [
                self.book_dir / self.book_name / "images",
                self.book_dir / "peterpan" / "images"
            ]
            for dir_path in possible_dirs:
                if dir_path.exists():
                    character_dir = dir_path
                    break
        
        cmd = [
            "python", "ai/consistent_scene_generator.py",
            "--scenes", str(self.book_dir / "scenes.json"),
            "--characters", str(character_dir),
            "-o", str(self.book_dir / "consistent_scenes"),
            "--delay", "2.0"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print("✅ Consistent scene images generated")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generating consistent scenes: {e}")
            raise
    
    def _copy_to_react_app(self):
        """Copy book data to React app"""
        print(f"\n📱 STEP 6: Copying to React app")
        print("-" * 50)
        
        react_data_dir = Path("frontend/public/data")
        react_images_dir = Path("frontend/public/images")
        
        # Create directories
        react_data_dir.mkdir(parents=True, exist_ok=True)
        (react_images_dir / "characters").mkdir(parents=True, exist_ok=True)
        (react_images_dir / "scenes").mkdir(parents=True, exist_ok=True)
        (react_images_dir / "environments").mkdir(parents=True, exist_ok=True)
        
        # Copy data files
        book_data_dir = react_data_dir / self.book_name
        book_data_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_copy = [
            ("analysis.json", "analysis.json"),
            ("character_prompts.json", "character_prompts.json"),
            ("scenes.json", "scenes.json")
        ]
        
        for src_file, dst_file in files_to_copy:
            src_path = self.book_dir / src_file
            dst_path = book_data_dir / dst_file
            if src_path.exists():
                shutil.copy2(src_path, dst_path)
                print(f"  📄 Copied: {src_file}")
        
        # Copy chapter structure if it exists
        chapters_src = self.book_dir / "chapters"
        if chapters_src.exists() and chapters_src.is_dir():
            chapters_dst = book_data_dir / "chapters"
            if chapters_dst.exists():
                shutil.rmtree(chapters_dst)
            shutil.copytree(chapters_src, chapters_dst)
            
            # Count chapters copied
            chapter_count = len([d for d in chapters_dst.iterdir() if d.is_dir()])
            print(f"  📚 Copied {chapter_count} chapter directories")
        
        # Copy images
        if (self.book_dir / "images").exists():
            for img_file in (self.book_dir / "images").glob("*.png"):
                dst_path = react_images_dir / "characters" / img_file.name
                shutil.copy2(img_file, dst_path)
                print(f"  🖼️  Copied character: {img_file.name}")
        
        if (self.book_dir / "consistent_scenes").exists():
            for img_file in (self.book_dir / "consistent_scenes").glob("*.png"):
                dst_path = react_images_dir / "scenes" / img_file.name
                shutil.copy2(img_file, dst_path)
                print(f"  🎬 Copied scene: {img_file.name}")
        
        if (self.book_dir / "environments").exists():
            for img_file in (self.book_dir / "environments").glob("*.png"):
                dst_path = react_images_dir / "environments" / img_file.name
                shutil.copy2(img_file, dst_path)
                print(f"  🌍 Copied environment: {img_file.name}")
        
        print("✅ Data copied to React app")
    
    def _update_react_book_list(self):
        """Update React app book list"""
        print(f"\n📚 STEP 7: Updating React book list")
        print("-" * 50)
        
        books_file = Path("frontend/public/data/books.json")
        
        # Load existing books or create new list
        if books_file.exists():
            with open(books_file) as f:
                books = json.load(f)
        else:
            books = []
        
        # Get book title from analysis if available
        book_title = self.book_name.replace('_', ' ').title()
        book_author = None
        analysis_file = self.book_dir / "analysis.json"
        
        if analysis_file.exists():
            with open(analysis_file) as f:
                analysis_data = json.load(f)
            # New format has book_title at top level
            if isinstance(analysis_data, dict):
                book_title = analysis_data.get('book_title', book_title)
                book_author = analysis_data.get('book_author')
        
        # Create description
        if book_author:
            description = f"Visual novel adaptation of {book_title} by {book_author}"
        else:
            description = f"Visual novel adaptation of {book_title}"
        
        # Add or update this book
        book_info = {
            "id": self.book_name,
            "title": book_title,
            "description": description,
            "data_dir": self.book_name,
            "created_at": str(Path().cwd()),
            "scenes_count": self._count_scenes(),
            "characters_count": self._count_characters()
        }
        
        # Remove existing entry if present
        books = [b for b in books if b["id"] != self.book_name]
        books.append(book_info)
        
        # Save updated list
        with open(books_file, 'w') as f:
            json.dump(books, f, indent=2)
        
        print(f"✅ Added book to React app: {book_info['title']}")
    
    def _get_selected_chapters(self) -> List[int]:
        """Get selected chapters from analysis file"""
        analysis_file = self.book_dir / "analysis.json"
        if analysis_file.exists():
            with open(analysis_file) as f:
                analysis_data = json.load(f)
            
            # Handle both old format (array) and new format (object with book_title)
            if isinstance(analysis_data, dict) and 'chapters' in analysis_data:
                chapters_list = analysis_data['chapters']
            else:
                chapters_list = analysis_data
            
            return [ch.get("chapter_number", i+1) for i, ch in enumerate(chapters_list)]
        return [1]  # fallback
    
    def _count_scenes(self) -> int:
        """Count scenes in scenes.json"""
        scenes_file = self.book_dir / "scenes.json"
        if scenes_file.exists():
            with open(scenes_file) as f:
                scenes = json.load(f)
            return len(scenes)
        return 0
    
    def _count_characters(self) -> int:
        """Count characters in analysis.json"""
        analysis_file = self.book_dir / "analysis.json"
        if analysis_file.exists():
            with open(analysis_file) as f:
                analysis_data = json.load(f)
            
            # Handle both old format (array) and new format (object with book_title)
            if isinstance(analysis_data, dict) and 'chapters' in analysis_data:
                chapters_list = analysis_data['chapters']
            else:
                chapters_list = analysis_data
            
            # Count unique characters across all chapters
            if chapters_list and len(chapters_list) > 0:
                all_characters = set()
                for chapter in chapters_list:
                    for char in chapter.get("characters", []):
                        all_characters.add(char.get("name", ""))
                return len(all_characters)
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Complete Book to Visual Novel Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive chapter selection
  %(prog)s books/alice.epub

  # Select specific chapters
  %(prog)s books/alice.epub --chapters 1,3,5

  # Custom output directory
  %(prog)s books/alice.epub -o my_books

  # Style is auto-detected by default
  %(prog)s books/alice.epub --chapters 1,2,3
  # → Detects "whimsical fantasy Victorian" style automatically
  
  %(prog)s books/lovecraft.epub --chapters 1,2
  # → Detects "dark gothic horror cosmic dread" style automatically

  # Style Override Examples (for creative variations):
  %(prog)s books/alice.epub --style "horror"          # Horror version of Alice
  %(prog)s books/alice.epub --style "cute kawaii"     # Cute version
  %(prog)s books/lovecraft.epub --style "cyberpunk"   # Cyberpunk Lovecraft
  %(prog)s books/lovecraft.epub --style "watercolor"  # Soft watercolor style
  %(prog)s books/alice.epub --style "teletubbies"     # Happy Teletubbies version!
        """
    )
    
    parser.add_argument(
        'epub_file',
        help='Path to EPUB file to convert'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Base output directory (default: output)'
    )
    
    parser.add_argument(
        '--chapters',
        help='Chapter selection: numbers (1,3,5), or keywords (demo, story, first, all)'
    )
    
    parser.add_argument(
        '--style',
        help='Override art style for the entire book. If not specified, style is auto-detected from book content. Examples: "horror", "cute kawaii", "cyberpunk neon", "watercolor pastel"'
    )
    
    parser.add_argument(
        '--resume-from',
        choices=['parse', 'analyze', 'characters', 'scenes', 'structure', 'consistent', 'copy', 'update'],
        help='Resume pipeline from a specific step'
    )
    
    args = parser.parse_args()
    
    # Parse chapter selection
    selected_chapters = None
    if args.chapters:
        if args.chapters.lower() in ['demo', 'story', 'first', 'all']:
            selected_chapters = args.chapters.lower()
        else:
            try:
                selected_chapters = [int(x.strip()) for x in args.chapters.split(',')]
            except ValueError:
                print("❌ Error: Invalid chapter numbers. Use comma-separated integers (e.g., 1,3,5)")
                sys.exit(1)
    
    try:
        # Show style override if specified
        if args.style:
            print(f"🎨 Art Style Override: {args.style}")
            print(f"   This style will be applied to all images in the book")
            print()
        
        converter = BookToVNConverter(args.epub_file, args.output, art_style=args.style)
        converter.run_complete_pipeline(selected_chapters, args.resume_from)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
