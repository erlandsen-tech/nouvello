"""
AI-powered scene segmentation for visual novels
Breaks down chapter content into distinct, illustrated scenes
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
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


class SceneSegmentation:
    """AI-powered scene segmentation for visual novels"""
    
    def __init__(self):
        self.llm = MultiProviderLLM()
    
    def segment_chapter(self, chapter_content: str, chapter_title: str) -> List[SceneSegment]:
        """Segment a chapter into distinct scenes"""
        
        segmentation_prompt = f"""
You are an expert at analyzing literature and breaking it down into visual scenes for a visual novel.

Chapter: {chapter_title}
Content: {chapter_content}

Your task is to break this chapter into 8-15 distinct visual scenes. Each scene should:
1. Be a coherent narrative unit (2-4 paragraphs)
2. Have a clear visual setting
3. Include specific characters present
4. Have a distinct mood/atmosphere
5. Be suitable for illustration

For each scene, provide:
- A descriptive title (3-6 words)
- The scene content (2-4 paragraphs from the original text)
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

Make sure the JSON is valid and complete. Focus on creating visually distinct scenes that would work well in a visual novel format.
"""

        try:
            response = self.llm.generate_response(
                prompt=segmentation_prompt,
                model="anthropic.claude-3-sonnet-20240229-v1:0"
            )
            
            segments = self._parse_segmentation_response(response, chapter_content)
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


def main():
    """Test the scene segmentation"""
    if len(sys.argv) != 3:
        print("Usage: python scene_segmentation.py <input_dir> <output_dir>")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
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
    
    with open(analysis_file) as f:
        analysis_data = json.load(f)
    
    segmentation = SceneSegmentation()
    all_scenes = []
    
    for chapter in analysis_data:
        print(f"Segmenting: {chapter['chapter_title']}")
        
        # Get chapter content (you might need to load this from the original EPUB)
        chapter_content = chapter.get('scene_description', '') + " " + chapter.get('mood_description', '')
        
        scenes = segmentation.segment_chapter(chapter_content, chapter['chapter_title'])
        all_scenes.extend(scenes)
    
    # Save scenes
    scenes_file = output_dir / "scenes.json"
    with open(scenes_file, 'w') as f:
        json.dump([scene.__dict__ for scene in all_scenes], f, indent=2)
    
    print(f"✅ Generated {len(all_scenes)} scenes")
    print(f"📁 Saved to: {scenes_file}")


if __name__ == "__main__":
    main()
