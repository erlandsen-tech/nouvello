"""
Consistent Scene Image Generator
Uses existing character images as input to generate scene images with character consistency
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import argparse

# Add the ai directory to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gemini_image_generator import GeminiImageGenerator
except ImportError:
    # Try alternative import path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ai.gemini_image_generator import GeminiImageGenerator


@dataclass
class SceneSegment:
    """Represents a scene segment"""
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


class ConsistentSceneGenerator:
    """Generate scene images with consistent characters"""
    
    def __init__(self, art_style: Optional[str] = None):
        self.image_generator = GeminiImageGenerator()
        self.art_style = art_style  # Optional style override
    
    def generate_consistent_scenes(
        self, 
        scenes: List[SceneSegment], 
        character_images_dir: Path, 
        output_dir: Path,
        delay: float = 2.0
    ):
        """Generate consistent scene images for all scenes"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🎭 Generating {len(scenes)} consistent scene images...")
        print(f"📁 Character images: {character_images_dir}")
        print(f"📁 Output directory: {output_dir}")
        print(f"⏱️  Delay between requests: {delay}s")
        print()
        
        # Get number of workers from env (default to 2 for API rate limits)
        num_workers = int(os.getenv("SCENE_IMAGE_WORKERS", "2"))
        
        # Use parallel processing if multiple scenes
        if len(scenes) > 1 and num_workers > 1:
            # Don't create more workers than scenes
            actual_workers = min(num_workers, len(scenes))
            print(f"🚀 Running parallel scene generation with {actual_workers} workers")
            self._generate_scenes_parallel(scenes, character_images_dir, output_dir, actual_workers, delay)
        else:
            # Sequential for single scene or single worker
            for i, scene in enumerate(scenes, 1):
                print(f"🎬 [{i}/{len(scenes)}] Generating: {scene.title}")
                
                try:
                    # Find character images for this scene
                    character_refs = self._find_character_images(scene.characters_present, character_images_dir)
                    
                    if character_refs:
                        print(f"   👥 Using character references: {list(character_refs.keys())}")
                        image_path, was_generated = self._generate_scene_with_characters(
                            scene, character_refs, output_dir
                        )
                    else:
                        print(f"   🌍 No characters found, generating environment scene")
                        image_path, was_generated = self._generate_environment_scene(scene, output_dir)
                    
                    if image_path and was_generated:
                        print(f"   ✅ Generated: {image_path.name}")
                    elif not image_path:
                        print(f"   ❌ Failed to generate image")
                    
                    # Delay between requests
                    if i < len(scenes):
                        time.sleep(delay)
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    continue
        
        print(f"\n🎉 Scene generation complete!")
        print(f"📁 Check output directory: {output_dir}")
    
    def _generate_scenes_parallel(self, scenes: List[SceneSegment], character_dir: Path, output_dir: Path, num_workers: int, delay: float):
        """Generate scenes in parallel using threads (API-safe)"""
        def generate_single(scene_with_idx):
            i, scene = scene_with_idx
            print(f"🎬 [{i}/{len(scenes)}] Generating: {scene.title}")
            
            try:
                character_refs = self._find_character_images(scene.characters_present, character_dir)
                
                if character_refs:
                    print(f"   👥 Using character references: {list(character_refs.keys())}")
                    image_path, was_generated = self._generate_scene_with_characters(scene, character_refs, output_dir)
                else:
                    print(f"   🌍 No characters found, generating environment scene")
                    image_path, was_generated = self._generate_environment_scene(scene, output_dir)
                
                if image_path and was_generated:
                    print(f"   ✅ Generated: {image_path.name}")
                elif not image_path:
                    print(f"   ❌ Failed to generate image")
                
                # Delay after generation
                time.sleep(delay)
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(generate_single, (i, scene)) for i, scene in enumerate(scenes, 1)]
            [f.result() for f in futures]
    
    def _find_character_images(self, characters: List[str], character_dir: Path) -> Dict[str, Path]:
        """Find character image files for the given characters"""
        character_refs = {}
        
        for character in characters:
            # Try different naming patterns
            possible_names = [
                character.lower().replace(' ', '_'),
                character.lower().replace(' ', ''),
                character.lower(),
                character.replace(' ', '_'),
                character.replace(' ', '')
            ]
            
            for name in possible_names:
                image_path = character_dir / f"{name}.png"
                if image_path.exists():
                    character_refs[character] = image_path
                    break
        
        return character_refs
    
    def _generate_scene_with_characters(
        self, 
        scene: SceneSegment, 
        character_refs: Dict[str, Path], 
        output_dir: Path
    ) -> tuple[Optional[Path], bool]:
        """Generate a scene image using character references
        
        Returns:
            tuple: (image_path, was_generated) - was_generated is False if skipped
        """
        # Compute expected output path and skip if exists
        safe_title = scene.title.lower().replace(' ', '_').replace('-', '_').replace("'", '').replace('"', '')
        # Remove other special characters
        safe_title = ''.join(c for c in safe_title if c.isalnum() or c == '_')
        scene_name = f"scene_{scene.scene_number:02d}_{safe_title}"
        expected_path = output_dir / f"{scene_name}.png"
        if expected_path.exists():
            print(f"   ⏭️  Skipping scene (exists): {expected_path.name}")
            return expected_path, False  # Return path but mark as not generated

        # Get style override from analysis if available
        style_override = getattr(self, 'art_style', None)
        style_requirement = "- Visual novel art style\n- Professional anime/manga art style"
        if style_override:
            style_requirement = f"- **{style_override.upper()} STYLE** - This is MANDATORY for consistency\n- All elements must match the {style_override} aesthetic"
        
        # Create enhanced prompt with character consistency instructions
        enhanced_prompt = f"""
Create a detailed scene illustration for a visual novel with the following requirements:

SCENE: {scene.title}
SETTING: {scene.setting}
MOOD: {scene.mood}

CHARACTER CONSISTENCY REQUIREMENTS:
- Use the provided character reference images to maintain exact character appearance
- Characters must look identical to their reference images
- Maintain consistent clothing, hair, facial features, and body proportions
- Only change expressions/poses, not physical appearance

SCENE DESCRIPTION: {scene.image_prompt}

STYLE REQUIREMENTS:
{style_requirement}
- High quality, detailed illustration
- Appropriate lighting for the mood
- Clear character positioning
- Rich environmental details

The characters in this scene are: {', '.join(scene.characters_present)}
Make sure each character appears exactly as they do in their reference images.
"""
        
        # Generate the scene image with character references
        try:
            result = self.image_generator.generate_scene_with_references(
                scene_name=scene_name,
                prompt=enhanced_prompt,
                reference_images=character_refs,
                output_dir=str(output_dir)
            )
            if result.success:
                return Path(result.output_path), True  # Successfully generated
            else:
                print(f"   Error: {result.error_message}")
                return None, False
        except Exception as e:
            print(f"   Error generating scene with characters: {e}")
            return None, False
    
    def _generate_environment_scene(self, scene: SceneSegment, output_dir: Path) -> tuple[Optional[Path], bool]:
        """Generate an environment-only scene
        
        Returns:
            tuple: (image_path, was_generated) - was_generated is False if skipped
        """
        # Compute expected output path and skip if exists
        safe_title = scene.title.lower().replace(' ', '_').replace('-', '_').replace("'", '').replace('"', '')
        # Remove other special characters
        safe_title = ''.join(c for c in safe_title if c.isalnum() or c == '_')
        scene_name = f"scene_{scene.scene_number:02d}_{safe_title}"
        expected_path = output_dir / f"{scene_name}.png"
        if expected_path.exists():
            print(f"   ⏭️  Skipping scene (exists): {expected_path.name}")
            return expected_path, False  # Return path but mark as not generated

        # Get style override
        style_override = getattr(self, 'art_style', None)
        style_requirement = "- Visual novel art style\n- Professional anime/manga art style"
        if style_override:
            style_requirement = f"- **{style_override.upper()} STYLE** - This is MANDATORY\n- All elements must match the {style_override} aesthetic"
        
        env_prompt = f"""
Create a detailed environment illustration for a visual novel:

SCENE: {scene.title}
SETTING: {scene.setting}
MOOD: {scene.mood}

DESCRIPTION: {scene.image_prompt}

STYLE REQUIREMENTS:
{style_requirement}
- High quality, detailed illustration
- Appropriate lighting for the mood
- Rich environmental details
- No characters, focus on the setting and atmosphere
"""
        
        try:
            result = self.image_generator.generate_character_image(
                character_name=scene_name,
                prompt=env_prompt,
                output_dir=str(output_dir)
            )
            if result.success:
                return Path(result.output_path), True  # Successfully generated
            else:
                print(f"   Error: {result.error_message}")
                return None, False
        except Exception as e:
            print(f"   Error generating environment scene: {e}")
            return None, False


def main():
    parser = argparse.ArgumentParser(description="Generate consistent scene images")
    parser.add_argument("--scenes", required=True, help="Path to scenes.json file")
    parser.add_argument("--characters", required=True, help="Path to character images directory")
    parser.add_argument("-o", "--output", required=True, help="Output directory for scene images")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests in seconds")
    
    args = parser.parse_args()
    
    scenes_file = Path(args.scenes)
    character_dir = Path(args.characters)
    output_dir = Path(args.output)
    
    if not scenes_file.exists():
        print(f"❌ Scenes file not found: {scenes_file}")
        sys.exit(1)
    
    if not character_dir.exists():
        print(f"❌ Character directory not found: {character_dir}")
        sys.exit(1)
    
    # Load scenes
    with open(scenes_file) as f:
        scenes_data = json.load(f)
    
    scenes = [SceneSegment(**scene_data) for scene_data in scenes_data]
    
    # Load style from scenes or analysis file
    art_style = None
    analysis_file = Path(args.scenes).parent / "analysis.json"
    if analysis_file.exists():
        try:
            with open(analysis_file) as f:
                analysis = json.load(f)
                if isinstance(analysis, dict):
                    art_style = analysis.get('art_style')
                    if art_style:
                        print(f"🎨 Using art style override: {art_style}")
        except:
            pass
    
    # Check if all scene images already exist
    output_dir.mkdir(parents=True, exist_ok=True)
    all_exist = True
    for scene in scenes:
        safe_title = scene.title.lower().replace(' ', '_').replace('-', '_').replace("'", '').replace('"', '')
        # Remove other special characters
        safe_title = ''.join(c for c in safe_title if c.isalnum() or c == '_')
        scene_name = f"scene_{scene.scene_number:02d}_{safe_title}"
        expected_path = output_dir / f"{scene_name}.png"
        if not expected_path.exists():
            all_exist = False
            break
    
    if all_exist:
        print(f"✅ All {len(scenes)} scene images already exist: {output_dir}")
        print(f"   ⏭️  Skipping scene image generation (all files exist)")
        print(f"\n💡 To regenerate scene images, delete {output_dir}/ and run again")
        sys.exit(0)
    
    # Generate consistent scenes
    generator = ConsistentSceneGenerator(art_style=art_style)
    generator.generate_consistent_scenes(scenes, character_dir, output_dir, args.delay)


if __name__ == "__main__":
    main()
