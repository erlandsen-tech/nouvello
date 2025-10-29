"""
AI-powered scene segmentation for visual novels
Breaks down chapter content into distinct, illustrated scenes
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

# Add the ai directory to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from llm_providers import MultiProviderLLM
except ImportError:
    # Try alternative import path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ai.llm_providers import MultiProviderLLM


@dataclass
class SceneSegment:
    """Represents a segmented scene from chapter content"""
    scene_number: int
    title: str
    content: str
    characters_present: List[str]
    setting: str
    mood: str
    image_prompt: str
    image_type: str
    image_file: str
    chapter_number: int = 0  # Chapter this scene belongs to
    chapter_title: str = ""  # Chapter title


class SceneSegmentation:
    """AI-powered scene segmentation for visual novels"""
    
    def __init__(self, model: Optional[str] = None):
        # Load environment variables
        load_dotenv()
        self.llm = MultiProviderLLM()
        # Allow override via parameter or env, default to fast model for iteration
        self.model = model or os.getenv("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
    
    def segment_chapter(self, chapter_content: str, chapter_title: str) -> List[SceneSegment]:
        """Segment a chapter into distinct scenes"""
        
        segmentation_prompt = f"""
You are an expert at analyzing literature and breaking it down into visual scenes for a visual novel.

Chapter: {chapter_title}
Content: {chapter_content}

Your task is to break this chapter into distinct visual scenes (minimum 4 scenes, but use more if the content warrants it, typically 8-15). Each scene should:
1. Be a coherent narrative unit (2-4 paragraphs)
2. Have a clear visual setting
3. Include specific characters present
4. Have a distinct mood/atmosphere
5. Be suitable for illustration
6. Keep the books narrative style and tone

For each scene, provide:
- A descriptive title (3-6 words)
- The scene content (ACTUAL PARAGRAPHS FROM THE ORIGINAL TEXT, 2-4 paragraphs - this is what will be read in the visual novel!)
- Characters present (list of character names)
- Setting description (where the scene takes place)
- Mood description (the emotional atmosphere)
- Image prompt (detailed description for AI image generation)
- Image type (always "scene")

Return your response as a JSON array with this exact structure:
[
  {{
    "scene_number": 1,
    "title": "Scene Title",
    "content": "Scene content here...",
    "characters_present": ["Character1", "Character2"],
    "setting": "Detailed setting description",
    "mood": "Mood description",
    "image_prompt": "Detailed image generation prompt",
    "image_type": "scene",
    "image_file": "scene_01_scene_title.png"
  }}
]

IMPORTANT: The "content" field must contain the ACTUAL ORIGINAL TEXT from the chapter that will be displayed to the reader. Do NOT write a description of the scene - copy the actual narrative text (2-4 paragraphs) that tells the story. This content is what appears in the text panel of the visual novel.

Make sure the JSON is valid and complete. Focus on creating visually distinct scenes with original narrative text that works well in a visual novel format.
"""

        try:
            response = self.llm.generate_response(
                prompt=segmentation_prompt,
                model=self.model
            )
            
            segments = self._parse_segmentation_response(response, chapter_content)
            
            # Ensure minimum 4 scenes (split if needed)
            if len(segments) < 4:
                print(f"⚠️  Warning: Only {len(segments)} scenes generated. Need at least 4.")
                segments = self._ensure_minimum_scenes(segments, chapter_content, chapter_title)
            
            return segments
            
        except Exception as e:
            print(f"Error in scene segmentation: {e}")
            # Fallback: create a single scene
            return [SceneSegment(
                scene_number=1,
                title=chapter_title,
                content=chapter_content[:500] + "..." if len(chapter_content) > 500 else chapter_content,
                characters_present=[],
                setting="Unknown setting",
                mood="Neutral",
                image_prompt=f"Scene from {chapter_title}",
                image_type="scene",
                image_file="scene_01_default.png"
            )]

    def _window_text(self, text: str, window_size: int, overlap: int) -> List[Tuple[int, str]]:
        """Split text into overlapping windows. Returns list of (index, slice)."""
        if window_size <= 0:
            return [(0, text)]
        if overlap < 0:
            overlap = 0
        windows: List[Tuple[int, str]] = []
        step = max(1, window_size - overlap)
        start = 0
        idx = 0
        while start < len(text):
            end = min(len(text), start + window_size)
            windows.append((idx, text[start:end]))
            idx += 1
            if end == len(text):
                break
            start = start + step
        return windows

    def segment_chapter_windowed(
        self,
        chapter_content: str,
        chapter_title: str,
        window_size: int,
        overlap: int,
        workers: int = 4
    ) -> List[SceneSegment]:
        """Segment a chapter by applying segmentation over overlapping windows in parallel, then reduce."""
        windows = self._window_text(chapter_content, window_size, overlap)
        if len(windows) == 1:
            return self.segment_chapter(chapter_content, chapter_title)

        # Small chapter outline for global context
        outline_prompt = f"""
You will receive a chapter chunk and must propose visual-novel scenes from ACTUAL original text.
Keep narrative voice. The final app shows the "content" field verbatim to the user.
""".strip()

        def process_window(win_idx: int, win_text: str) -> List[SceneSegment]:
            prompt = f"{outline_prompt}\n\n[Window {win_idx+1}/{len(windows)} of chapter '{chapter_title}']\n\n{win_text}"
            try:
                response = self.llm.generate_response(
                    prompt=self._build_window_prompt(chapter_title, prompt),
                    model=self.model
                )
                return self._parse_segmentation_response(response, win_text)
            except Exception as e:
                print(f"   ❌ Window {win_idx+1} failed: {e}")
                return []

        results: List[SceneSegment] = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {executor.submit(process_window, i, t): i for i, t in windows}
            for fut in as_completed(futures):
                results.extend(fut.result())

        # Reduce: merge consecutive duplicates by normalized title, renumber
        def norm_title(t: str) -> str:
            return (t or "").lower().strip()

        merged: List[SceneSegment] = []
        seen_titles: set = set()
        for seg in results:
            key = norm_title(seg.title)
            # Keep first occurrence of a title; prefer longer content
            if key in seen_titles:
                # If duplicate title appears, replace previous if new content is longer
                for i in range(len(merged)-1, -1, -1):
                    if norm_title(merged[i].title) == key:
                        if len(seg.content) > len(merged[i].content):
                            merged[i] = seg
                        break
                continue
            seen_titles.add(key)
            merged.append(seg)

        # Ensure minimum 4 scenes using existing helper
        merged = self._ensure_minimum_scenes(merged, chapter_content, chapter_title)

        # Renumber and sanitize filenames
        for i, seg in enumerate(merged, 1):
            seg.scene_number = i
            safe_title = seg.title.lower().replace(' ', '_').replace('-', '_').replace("'", '').replace('"', '')
            # Remove other special characters for safe filenames
            safe_title = ''.join(c for c in safe_title if c.isalnum() or c == '_')
            seg.image_file = f"scene_{i:02d}_{safe_title}.png"
        return merged

    def _build_window_prompt(self, chapter_title: str, window_text: str) -> str:
        """Prompt specialized for windowed segmentation; keeps JSON schema identical."""
        return f"""
You are an expert at breaking literature into visual-novel scenes.
Chapter: {chapter_title}
Chunk Content:
{window_text}

Your task is to propose scenes from this chunk ONLY (minimum 1 if meaningful). Each scene should:
1. Be a coherent narrative unit (2–4 paragraphs of ORIGINAL TEXT)
2. Include characters present, setting, mood
3. Provide an image prompt for illustration

Return JSON array with fields: scene_number, title, content (ORIGINAL TEXT), characters_present, setting, mood, image_prompt, image_type ("scene"), image_file.
"""
    
    def _parse_segmentation_response(self, response, original_content: str) -> List[SceneSegment]:
        """Parse AI response into SceneSegment objects."""
        try:
            # Extract content from LLMResponse object
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON array found in response")
            
            json_str = content[json_start:json_end]
            segments_data = json.loads(json_str)
            
            segments = []
            for i, seg_data in enumerate(segments_data):
                segment = SceneSegment(
                    scene_number=i + 1,
                    title=seg_data.get('title', f'Scene {i + 1}'),
                    content=seg_data.get('content', ''),
                    characters_present=seg_data.get('characters_present', []),
                    setting=seg_data.get('setting', 'Unknown'),
                    mood=seg_data.get('mood', 'Neutral'),
                    image_prompt=seg_data.get('image_prompt', ''),
                    image_type=seg_data.get('image_type', 'scene'),
                    image_file=seg_data.get('image_file', f'scene_{i+1:02d}_default.png')
                )
                segments.append(segment)
            
            return segments
            
        except Exception as e:
            print(f"Error parsing segmentation response: {e}")
            # Fallback: create a single scene
            return [SceneSegment(
                scene_number=1,
                title="Default Scene",
                content=original_content[:500] + "..." if len(original_content) > 500 else original_content,
                characters_present=[],
                setting="Unknown setting",
                mood="Neutral",
                image_prompt="Default scene",
                image_type="scene",
                image_file="scene_01_default.png"
            )]
    
    def _ensure_minimum_scenes(self, segments: List[SceneSegment], 
                               chapter_content: str, chapter_title: str) -> List[SceneSegment]:
        """Ensure we have at least 4 scenes by splitting longer scenes if needed."""
        if len(segments) >= 4:
            return segments
        
        # If all segmentation attempts failed, create a fallback scene
        if len(segments) == 0:
            print(f"⚠️  No scenes generated - creating fallback scene from chapter content")
            # Create a single basic scene from the chapter
            return [SceneSegment(
                scene_number=1,
                title=chapter_title or "Chapter Scene",
                content=chapter_content[:2000] if len(chapter_content) > 2000 else chapter_content,
                characters_present=["Unknown"],
                setting="Scene from the chapter",
                mood="neutral",
                image_prompt=f"Illustration for {chapter_title}",
                image_type="scene",
                image_file="scene_01_fallback.png"
            )]
        
        # If we have just 1-3 scenes, we need to create more
        print(f"📝 Splitting scenes to reach minimum of 4...")
        
        # Calculate how many extra scenes we need
        extra_needed = 4 - len(segments)
        
        # Split the longest scene(s) into multiple sub-scenes
        expanded_segments = []
        scene_num = 1
        
        for segment in segments:
            # If we still need more scenes and this segment is long enough
            if extra_needed > 0 and len(segment.content) > 300:
                # Split this segment into 2 parts
                mid_point = len(segment.content) // 2
                first_half = segment.content[:mid_point]
                second_half = segment.content[mid_point:]
                
                # Create first half
                expanded_segments.append(SceneSegment(
                    scene_number=scene_num,
                    title=f"{segment.title} (Part 1)",
                    content=first_half,
                    characters_present=segment.characters_present,
                    setting=segment.setting,
                    mood=segment.mood,
                    image_prompt=segment.image_prompt,
                    image_type=segment.image_type,
                    image_file=f"scene_{scene_num:02d}_part1.png"
                ))
                scene_num += 1
                
                # Create second half
                expanded_segments.append(SceneSegment(
                    scene_number=scene_num,
                    title=f"{segment.title} (Part 2)",
                    content=second_half,
                    characters_present=segment.characters_present,
                    setting=segment.setting,
                    mood=segment.mood,
                    image_prompt=segment.image_prompt,
                    image_type=segment.image_type,
                    image_file=f"scene_{scene_num:02d}_part2.png"
                ))
                scene_num += 1
                extra_needed -= 1
            else:
                # Keep scene as-is
                expanded_segments.append(SceneSegment(
                    scene_number=scene_num,
                    title=segment.title,
                    content=segment.content,
                    characters_present=segment.characters_present,
                    setting=segment.setting,
                    mood=segment.mood,
                    image_prompt=segment.image_prompt,
                    image_type=segment.image_type,
                    image_file=segment.image_file
                ))
                scene_num += 1
        
        # Update scene numbers to be sequential
        for i, seg in enumerate(expanded_segments, 1):
            seg.scene_number = i
        
        # If we still don't have enough, duplicate the last scene
        while len(expanded_segments) < 4:
            last_seg = expanded_segments[-1]
            expanded_segments.append(SceneSegment(
                scene_number=len(expanded_segments) + 1,
                title=f"{last_seg.title} (Continued)",
                content=last_seg.content,
                characters_present=last_seg.characters_present,
                setting=last_seg.setting,
                mood=last_seg.mood,
                image_prompt=last_seg.image_prompt,
                image_type=last_seg.image_type,
                image_file=f"scene_{len(expanded_segments) + 1:02d}_continued.png"
            ))
        
        return expanded_segments


def main():
    """Test the scene segmentation"""
    import argparse
    parser = argparse.ArgumentParser(description="Generate scene segmentation")
    parser.add_argument("input_dir", help="Book output directory (contains analysis.json)")
    parser.add_argument("output_dir", help="Directory to write scenes.json")
    parser.add_argument("--model", help="LLM model to use", default=os.getenv("BEDROCK_MODEL"))
    parser.add_argument("--windowed", action="store_true", help="Enable windowed overlapping segmentation")
    parser.add_argument("--window-size", type=int, default=int(os.getenv("SEG_WINDOW_SIZE", "4000")), help="Window size in characters")
    parser.add_argument("--window-overlap", type=int, default=int(os.getenv("SEG_WINDOW_OVERLAP", "500")), help="Overlap between windows in characters")
    parser.add_argument("--workers", type=int, default=int(os.getenv("SEG_WORKERS", "4")), help="Parallel workers for windows within each chapter")
    parser.add_argument("--chapter-workers", type=int, default=int(os.getenv("CHAPTER_SEG_WORKERS", "1")), help="Parallel workers for processing multiple chapters (default: 1)")
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load analysis data - try different possible locations
    possible_analysis_files = [
        input_dir / "analysis.json",
        input_dir / f"{input_dir.name}_analysis.json",
        input_dir / "peterpan" / "analysis.json",
        input_dir / "peterpan" / f"{input_dir.name}_analysis.json"
    ]
    
    analysis_file = None
    for file_path in possible_analysis_files:
        if file_path.exists():
            analysis_file = file_path
            break
    
    if not analysis_file:
        print(f"Analysis file not found. Tried:")
        for file_path in possible_analysis_files:
            print(f"  - {file_path}")
        sys.exit(1)
    
    print(f"📖 Using analysis file: {analysis_file}")
    
    # Check if scenes.json already exists
    scenes_file = output_dir / "scenes.json"
    if scenes_file.exists():
        print(f"✅ Scene segmentation already exists: {scenes_file}")
        print(f"   ⏭️  Skipping scene generation (file already exists)")
        print(f"\n💡 To regenerate scenes, delete {scenes_file} and run again")
        sys.exit(0)
    
    with open(analysis_file) as f:
        analysis_data = json.load(f)
    
    # Handle both old format (array) and new format (object with book_title)
    if isinstance(analysis_data, dict) and 'chapters' in analysis_data:
        chapters_list = analysis_data['chapters']
    else:
        chapters_list = analysis_data
    
    segmentation = SceneSegmentation(model=args.model)
    all_scenes = []
    
    # Determine if we should parallelize chapter processing
    chapter_workers = args.chapter_workers if hasattr(args, 'chapter_workers') else int(os.getenv("CHAPTER_SEG_WORKERS", "1"))
    use_parallel_chapters = len(chapters_list) > 1 and chapter_workers > 1
    
    def segment_single_chapter(chapter_data):
        """Process a single chapter (for parallel execution)"""
        chapter, seg_instance = chapter_data
        print(f"Segmenting: {chapter['chapter_title']}")
        
        # Get the full original chapter content for segmentation
        chapter_content = chapter.get('raw_content', '')
        
        # Fallback to descriptions if raw_content not available
        if not chapter_content or len(chapter_content) < 100:
            print(f"⚠️  Warning: No raw_content found, using descriptions as fallback")
            chapter_content = chapter.get('scene_description', '') + " " + chapter.get('mood_description', '')
        
        if args.windowed:
            scenes = seg_instance.segment_chapter_windowed(
                chapter_content,
                chapter['chapter_title'],
                window_size=max(1000, args.window_size),
                overlap=max(0, args.window_overlap),
                workers=max(1, args.workers)
            )
        else:
            scenes = seg_instance.segment_chapter(chapter_content, chapter['chapter_title'])
        
        # Add chapter information to each scene
        for scene in scenes:
            scene.chapter_number = chapter.get('chapter_number', 0)
            scene.chapter_title = chapter.get('chapter_title', '')
        
        return scenes
    
    if use_parallel_chapters:
        print(f"🚀 Processing {len(chapters_list)} chapters in parallel with {chapter_workers} workers")
        
        # Create chapter data tuples
        chapter_tasks = [(ch, segmentation) for ch in chapters_list]
        
        with ThreadPoolExecutor(max_workers=min(chapter_workers, len(chapters_list))) as executor:
            futures = {executor.submit(segment_single_chapter, task): i for i, task in enumerate(chapter_tasks)}
            for future in as_completed(futures):
                try:
                    scenes = future.result()
                    all_scenes.extend(scenes)
                except Exception as e:
                    print(f"❌ Error processing chapter: {e}")
    else:
        # Sequential processing (original behavior)
        for chapter in chapters_list:
            scenes = segment_single_chapter((chapter, segmentation))
            all_scenes.extend(scenes)
    
    # Save scenes
    scenes_file = output_dir / "scenes.json"
    with open(scenes_file, 'w') as f:
        json.dump([scene.__dict__ for scene in all_scenes], f, indent=2)
    
    print(f"✅ Generated {len(all_scenes)} scenes")
    print(f"📁 Saved to: {scenes_file}")


if __name__ == "__main__":
    main()
