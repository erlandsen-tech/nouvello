"""
Consistent Scene Image Generator
Uses existing character images as input to generate scene images with character consistency
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
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


class ConsistentSceneGenerator:
    """Generate scene images with consistent characters"""
    
    def __init__(self):
        self.image_generator = GeminiImageGenerator()
    
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
        
        for i, scene in enumerate(scenes, 1):
            print(f"🎬 [{i}/{len(scenes)}] Generating: {scene.title}")
            
            try:
                # Find character images for this scene
                character_refs = self._find_character_images(scene.characters_present, character_images_dir)
                
                if character_refs:
                    print(f"   👥 Using character references: {list(character_refs.keys())}")
                    image_path = self._generate_scene_with_characters(
                        scene, character_refs, output_dir
                    )
                else:
                    print(f"   🌍 No characters found, generating environment scene")
                    image_path = self._generate_environment_scene(scene, output_dir)
                
                if image_path:
                    print(f"   ✅ Generated: {image_path.name}")
                else:
                    print(f"   ❌ Failed to generate image")
                
                # Delay between requests
                if i < len(scenes):
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
        
        print(f"\n🎉 Scene generation complete!")
        print(f"📁 Check output directory: {output_dir}")
    
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
    ) -> Optional[Path]:
        """Generate a scene image using character references"""
        
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
- Visual novel art style
- High quality, detailed illustration
- Appropriate lighting for the mood
- Clear character positioning
- Rich environmental details
- Professional anime/manga art style

The characters in this scene are: {', '.join(scene.characters_present)}
Make sure each character appears exactly as they do in their reference images.
"""
        
        # Generate the scene image
        try:
            result = self.image_generator.generate_character_image(
                character_name=f"scene_{scene.scene_number:02d}_{scene.title.lower().replace(' ', '_').replace('-', '_')}",
                prompt=enhanced_prompt,
                output_dir=str(output_dir)
            )
            if result.success:
                return Path(result.output_path)
            else:
                print(f"   Error: {result.error_message}")
                return None
        except Exception as e:
            print(f"   Error generating scene with characters: {e}")
            return None
    
    def _generate_environment_scene(self, scene: SceneSegment, output_dir: Path) -> Optional[Path]:
        """Generate an environment-only scene"""
        
        env_prompt = f"""
Create a detailed environment illustration for a visual novel:

SCENE: {scene.title}
SETTING: {scene.setting}
MOOD: {scene.mood}

DESCRIPTION: {scene.image_prompt}

STYLE REQUIREMENTS:
- Visual novel art style
- High quality, detailed illustration
- Appropriate lighting for the mood
- Rich environmental details
- Professional anime/manga art style
- No characters, focus on the setting and atmosphere
"""
        
        try:
            result = self.image_generator.generate_character_image(
                character_name=f"scene_{scene.scene_number:02d}_{scene.title.lower().replace(' ', '_').replace('-', '_')}",
                prompt=env_prompt,
                output_dir=str(output_dir)
            )
            if result.success:
                return Path(result.output_path)
            else:
                print(f"   Error: {result.error_message}")
                return None
        except Exception as e:
            print(f"   Error generating environment scene: {e}")
            return None


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
    
    # Generate consistent scenes
    generator = ConsistentSceneGenerator()
    generator.generate_consistent_scenes(scenes, character_dir, output_dir, args.delay)


if __name__ == "__main__":
    main()
