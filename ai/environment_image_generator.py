"""
Environment/Background Image Generator
Generates atmospheric background images from scene descriptions using Gemini
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from gemini_image_generator import GeminiImageGenerator
from llm_providers import MultiProviderLLM


@dataclass
class EnvironmentImagePrompt:
    """Container for environment image generation prompt"""
    scene_name: str
    image_prompt: str
    style_tags: List[str]
    key_visual_elements: List[str]
    mood: str
    
    def to_dict(self) -> dict:
        return {
            "scene_name": self.scene_name,
            "image_prompt": self.image_prompt,
            "style_tags": self.style_tags,
            "key_visual_elements": self.key_visual_elements,
            "mood": self.mood
        }


class EnvironmentImageGenerator:
    """Generate atmospheric background images for visual novel scenes"""
    
    def __init__(self, provider: str = "bedrock", region: str = "eu-central-1",
                 model: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0", profile: Optional[str] = None):
        """
        Initialize the environment image generator
        
        Args:
            provider: LLM provider for prompt generation
            region: AWS region
            model: Specific model to use
            profile: AWS profile name
        """
        self.llm = MultiProviderLLM(provider=provider, region=region, profile=profile)
        self.model = model
        self.image_generator = GeminiImageGenerator()
    
    def generate_environment_prompt(self, 
                                   scene_description: str,
                                   mood_description: str,
                                   chapter_title: str,
                                   significant_objects: List[Dict] = None) -> EnvironmentImagePrompt:
        """
        Generate an image prompt for an environment/background
        
        Args:
            scene_description: Physical description of the setting
            mood_description: Atmosphere and mood
            chapter_title: Chapter name for reference
            significant_objects: Optional list of important objects in the scene
            
        Returns:
            EnvironmentImagePrompt with detailed generation instructions
        """
        objects_text = ""
        if significant_objects:
            objects_text = "\n".join([
                f"- {obj.get('name', 'Object')}: {obj.get('description', 'No description')}"
                for obj in significant_objects[:5]
            ])
        
        prompt = f"""Generate a detailed image generation prompt for a visual novel background scene.

SCENE DESCRIPTION:
{scene_description}

MOOD/ATMOSPHERE:
{mood_description}

CHAPTER CONTEXT:
{chapter_title}

SIGNIFICANT OBJECTS/DETAILS:
{objects_text if objects_text else "Not specified"}

Generate a detailed image generation prompt suitable for Gemini Image API that:
1. Captures the physical setting and environment accurately
2. Reflects the mood and atmosphere
3. Includes appropriate lighting and time of day
4. Incorporates significant objects naturally
5. Creates an immersive, atmospheric scene
6. Uses cinematic, visual language
7. Is suitable as a background (no focus on people/characters)
8. Maintains consistency with the literary style

IMPORTANT: This is a BACKGROUND image for a visual novel. It should:
- Be wide-angle or establishing shot
- Have good composition for text overlay at the bottom
- Create atmosphere without being too busy
- Leave space where character sprites might appear

Provide response in JSON format:
{{
  "image_prompt": "Detailed prompt for background image generation (150-300 words)",
  "style_tags": ["cinematic", "atmospheric", "tag3", "tag4"],
  "key_visual_elements": ["element1", "element2", "element3"],
  "mood": "single word describing primary mood"
}}

The image_prompt should be a single, cohesive paragraph focused on the environment.
Respond with ONLY the JSON."""

        try:
            response = self.llm.generate_response(prompt, model=self.model)
            
            # Parse JSON response
            content = response.content.strip()
            
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            # Create a simple scene name from chapter
            scene_name = chapter_title.lower().replace(" ", "_")[:30]
            
            return EnvironmentImagePrompt(
                scene_name=scene_name,
                image_prompt=data.get("image_prompt", ""),
                style_tags=data.get("style_tags", []),
                key_visual_elements=data.get("key_visual_elements", []),
                mood=data.get("mood", "atmospheric")
            )
            
        except Exception as e:
            print(f"Error generating environment prompt: {e}")
            # Fallback prompt
            return EnvironmentImagePrompt(
                scene_name=chapter_title.lower().replace(" ", "_")[:30],
                image_prompt=f"{scene_description} {mood_description}",
                style_tags=["atmospheric", "cinematic"],
                key_visual_elements=["setting", "environment"],
                mood="atmospheric"
            )
    
    def generate_environment_image(self,
                                   prompt: EnvironmentImagePrompt,
                                   output_path: Path,
                                   aspect_ratio: str = "16:9") -> Path:
        """
        Generate an environment image using Gemini
        
        Args:
            prompt: EnvironmentImagePrompt with generation details
            output_path: Where to save the image
            aspect_ratio: Image aspect ratio (16:9 for backgrounds)
            
        Returns:
            Path to generated image
        """
        print(f"Generating environment: {prompt.scene_name}")
        print(f"  Prompt: {prompt.image_prompt[:100]}...")
        
        try:
            # Generate image using Gemini  
            # Use the character image generation method with appropriate parameters
            result = self.image_generator.generate_character_image(
                character_name=prompt.scene_name,
                prompt=prompt.image_prompt,
                output_dir=str(output_path.parent),
                aspect_ratio=aspect_ratio
            )
            
            # Rename to our desired filename
            if result.success and Path(result.output_path).exists():
                final_path = output_path
                Path(result.output_path).rename(final_path)
                print(f"  ✓ Generated: {final_path}")
                return final_path
            else:
                raise Exception(result.error_message or "Image generation failed")
            
        except Exception as e:
            print(f"  ✗ Error generating environment image: {e}")
            raise
    
    def generate_from_analysis(self,
                               analysis_file: Path,
                               output_dir: Path,
                               generate_variations: bool = False) -> Dict[str, Path]:
        """
        Generate environment images from a chapter analysis file
        
        Args:
            analysis_file: Path to analysis.json
            output_dir: Directory to save images
            generate_variations: If True, generate multiple mood variations
            
        Returns:
            Dictionary mapping scene names to image paths
        """
        # Load analysis
        with open(analysis_file) as f:
            analysis = json.load(f)
            if isinstance(analysis, list):
                analysis = analysis[0]
        
        scene_desc = analysis.get("scene_description", "")
        mood_desc = analysis.get("mood_description", "")
        chapter_title = analysis.get("chapter_title", "Scene")
        objects = analysis.get("significant_objects", [])
        
        if not scene_desc:
            print("Warning: No scene description found in analysis")
            return {}
        
        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_images = {}
        
        # Generate main environment prompt
        print(f"\nGenerating environment for: {chapter_title}")
        env_prompt = self.generate_environment_prompt(
            scene_desc,
            mood_desc,
            chapter_title,
            objects
        )
        
        # Save prompt for reference
        prompt_file = output_dir / f"{env_prompt.scene_name}_prompt.json"
        with open(prompt_file, 'w') as f:
            json.dump(env_prompt.to_dict(), f, indent=2)
        print(f"Saved prompt: {prompt_file}")
        
        # Generate main background
        main_bg_path = output_dir / f"{env_prompt.scene_name}.png"
        try:
            image_path = self.generate_environment_image(
                env_prompt,
                main_bg_path
            )
            generated_images["main"] = image_path
        except Exception as e:
            print(f"Failed to generate main background: {e}")
        
        # Optionally generate variations (different times of day, etc.)
        if generate_variations:
            variations = ["night", "dusk", "foggy"]
            for variation in variations:
                var_prompt = EnvironmentImagePrompt(
                    scene_name=f"{env_prompt.scene_name}_{variation}",
                    image_prompt=f"{env_prompt.image_prompt}. Rendered at {variation} time with appropriate lighting and atmosphere.",
                    style_tags=env_prompt.style_tags + [variation],
                    key_visual_elements=env_prompt.key_visual_elements,
                    mood=variation
                )
                
                var_path = output_dir / f"{var_prompt.scene_name}.png"
                try:
                    image_path = self.generate_environment_image(var_prompt, var_path)
                    generated_images[variation] = image_path
                except Exception as e:
                    print(f"Failed to generate {variation} variation: {e}")
        
        return generated_images


def main():
    """Command line interface for environment image generation"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python environment_image_generator.py <analysis.json> [output_dir] [--variations]")
        print()
        print("Examples:")
        print("  python environment_image_generator.py output/BookName/analysis.json")
        print("  python environment_image_generator.py output/BookName/analysis.json output/BookName/environments")
        print("  python environment_image_generator.py output/BookName/analysis.json output/BookName/environments --variations")
        sys.exit(1)
    
    analysis_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else analysis_file.parent / "environments"
    generate_variations = "--variations" in sys.argv
    
    if not analysis_file.exists():
        print(f"Error: Analysis file not found: {analysis_file}")
        sys.exit(1)
    
    print("=" * 70)
    print("🌆 Environment Image Generator")
    print("=" * 70)
    print()
    
    generator = EnvironmentImageGenerator()
    
    try:
        images = generator.generate_from_analysis(
            analysis_file,
            output_dir,
            generate_variations=generate_variations
        )
        
        print()
        print("=" * 70)
        print("✓ Environment Generation Complete!")
        print("=" * 70)
        print(f"\nGenerated {len(images)} images:")
        for name, path in images.items():
            print(f"  {name}: {path}")
        print()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

