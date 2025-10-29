"""
Gemini Image Generator
Generates images using Google's Gemini Image Generation API
Reads character prompts and generates corresponding images
"""

import os
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Check if google.genai is available
try:
    
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  Warning: google-genai not installed. Install with: pip install google-genai")


@dataclass
class GeneratedImage:
    """Represents a generated image"""
    character_name: str
    prompt_used: str
    output_path: str
    aspect_ratio: str = "1:1"
    generation_time: float = 0.0
    success: bool = True
    error_message: str = ""


class GeminiImageGenerator:
    """Generate images using Gemini Image API"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the image generator
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY from .env)
            model: Model to use for generation (defaults to GEMINI_MODEL from .env or gemini-2.5-flash-image)
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai package not installed. Install with: pip install google-genai")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set GEMINI_API_KEY in .env file or pass api_key parameter")
        
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-image")
        self.client = genai.Client(api_key=self.api_key)
    
    def generate_character_image(self, character_name: str, prompt: str, 
                                output_dir: str, aspect_ratio: str = "1:1") -> GeneratedImage:
        """
        Generate an image for a single character
        
        Args:
            character_name: Name of the character
            prompt: Image generation prompt
            output_dir: Directory to save generated image
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 3:4, 4:3, etc.)
            
        Returns:
            GeneratedImage object with generation results
        """
        start_time = time.time()
        
        # Sanitize filename
        safe_name = "".join(c for c in character_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        output_path = os.path.join(output_dir, f"{safe_name}.png")
        
        # Check if image already exists
        if Path(output_path).exists():
            print(f"  ⏭️  Skipping {character_name} - image already exists")
            return GeneratedImage(
                character_name=character_name,
                prompt_used=prompt,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                generation_time=0.0,
                success=True
            )
        
        try:
            print(f"  🎨 Generating image for: {character_name}")
            
            # Generate image with Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )
            )
            
            # Extract image from response
            image_saved = False
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(f"     ℹ️  Model response: {part.text[:100]}")
                elif part.inline_data is not None:
                    # Save the image
                    image = Image.open(BytesIO(part.inline_data.data))
                    image.save(output_path)
                    image_saved = True
                    print(f"     ✅ Image saved: {output_path}")
            
            if not image_saved:
                raise ValueError("No image data in response")
            
            generation_time = time.time() - start_time
            
            return GeneratedImage(
                character_name=character_name,
                prompt_used=prompt,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                generation_time=generation_time,
                success=True
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            print(f"     ❌ Error: {str(e)}")
            
            return GeneratedImage(
                character_name=character_name,
                prompt_used=prompt,
                output_path="",
                aspect_ratio=aspect_ratio,
                generation_time=generation_time,
                success=False,
                error_message=str(e)
            )
    
    def generate_scene_with_references(self, scene_name: str, prompt: str,
                                      reference_images: Dict[str, Path],
                                      output_dir: str, aspect_ratio: str = "16:9") -> GeneratedImage:
        """
        Generate a scene image using character reference images
        
        Args:
            scene_name: Name for the scene
            prompt: Scene description prompt
            reference_images: Dict mapping character names to their image paths
            output_dir: Directory to save generated image
            aspect_ratio: Aspect ratio for the scene image
            
        Returns:
            GeneratedImage object with generation results
        """
        start_time = time.time()
        
        # Sanitize filename
        safe_name = "".join(c for c in scene_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        output_path = os.path.join(output_dir, f"{safe_name}.png")
        
        try:
            print(f"  🎬 Generating scene: {scene_name}")
            print(f"     📸 Using {len(reference_images)} character references")
            
            # Build contents array with reference images
            contents = []
            
            # Add reference images as PIL Image objects
            for char_name, image_path in reference_images.items():
                ref_image = Image.open(image_path)
                contents.append(ref_image)
                print(f"     📸 Loading reference: {char_name}")
            
            # Add the text prompt after images
            contents.append(prompt)
            
            # Generate image with Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )
            )
            
            # Extract image from response
            image_saved = False
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(f"     ℹ️  Model response: {part.text[:100]}")
                elif part.inline_data is not None:
                    # Save the image
                    image = Image.open(BytesIO(part.inline_data.data))
                    image.save(output_path)
                    image_saved = True
                    print(f"     ✅ Scene image saved: {output_path}")
            
            if not image_saved:
                raise ValueError("No image data in response")
            
            generation_time = time.time() - start_time
            
            return GeneratedImage(
                character_name=scene_name,
                prompt_used=prompt,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                generation_time=generation_time,
                success=True
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            print(f"     ❌ Error: {str(e)}")
            
            return GeneratedImage(
                character_name=scene_name,
                prompt_used=prompt,
                output_path="",
                aspect_ratio=aspect_ratio,
                generation_time=generation_time,
                success=False,
                error_message=str(e)
            )
    
    def generate_from_prompts_file(self, prompts_file: str, output_dir: str,
                                  aspect_ratio: str = "1:1",
                                  delay_seconds: float = 1.0) -> List[GeneratedImage]:
        """
        Generate images for all characters from a prompts JSON file
        
        Args:
            prompts_file: Path to JSON file with character prompts
            output_dir: Directory to save generated images
            aspect_ratio: Aspect ratio for all images
            delay_seconds: Delay between API calls to avoid rate limits
            
        Returns:
            List of GeneratedImage objects
        """
        print(f"📖 Loading prompts from: {prompts_file}")
        
        with open(prompts_file, 'r', encoding='utf-8') as f:
            prompts_data = json.load(f)
        
        print(f"✅ Loaded {len(prompts_data)} character prompts")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 Output directory: {output_dir}")
        
        # Get number of workers from env (default to 2 for API rate limits)
        num_workers = int(os.getenv("CHARACTER_IMAGE_WORKERS", "2"))
        
        # Generate images in parallel if multiple characters
        if len(prompts_data) > 1 and num_workers > 1:
            # Don't create more workers than characters
            actual_workers = min(num_workers, len(prompts_data))
            print(f"🚀 Running parallel image generation with {actual_workers} workers")
            results = self._generate_images_parallel(prompts_data, output_dir, aspect_ratio, actual_workers, delay_seconds)
        else:
            # Sequential for single character or single worker
            results = []
            total = len(prompts_data)
            
            for idx, prompt_data in enumerate(prompts_data, 1):
                char_name = prompt_data.get("character_name", f"Character_{idx}")
                image_prompt = prompt_data.get("image_prompt", "")
                
                print(f"\n[{idx}/{total}] {char_name}")
                
                result = self.generate_character_image(
                    char_name,
                    image_prompt,
                    output_dir,
                    aspect_ratio
                )
                results.append(result)
                
                # Delay between requests to avoid rate limits
                if idx < total and delay_seconds > 0:
                    time.sleep(delay_seconds)
        
        return results
    
    def _generate_images_parallel(self, prompts_data: List, output_dir: str, aspect_ratio: str, num_workers: int, delay_seconds: float) -> List[GeneratedImage]:
        """Generate images in parallel using threads (API-safe)"""
        results = []
        
        def generate_single(prompt_item):
            idx, prompt_data = prompt_item
            char_name = prompt_data.get("character_name", f"Character_{idx}")
            image_prompt = prompt_data.get("image_prompt", "")
            total = len(prompts_data)
            
            print(f"\n[{idx}/{total}] {char_name}")
            result = self.generate_character_image(char_name, image_prompt, output_dir, aspect_ratio)
            
            # Delay after generation
            time.sleep(delay_seconds)
            return result
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(generate_single, (idx+1, data)) for idx, data in enumerate(prompts_data)]
            results = [f.result() for f in futures]
        
        return results
    
    def export_generation_report(self, results: List[GeneratedImage], output_path: str):
        """
        Export generation results to a report file
        
        Args:
            results: List of GeneratedImage objects
            output_path: Path to save report
        """
        # Prepare report data
        report = {
            "total_characters": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_time_seconds": sum(r.generation_time for r in results),
            "results": [
                {
                    "character_name": r.character_name,
                    "output_path": r.output_path,
                    "aspect_ratio": r.aspect_ratio,
                    "generation_time": round(r.generation_time, 2),
                    "success": r.success,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Generation report saved: {output_path}")


def main():
    """Command-line interface"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate character images using Gemini API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate images from prompts file
  %(prog)s prompts.json -o images/

  # Use 16:9 aspect ratio
  %(prog)s prompts.json -o images/ --aspect-ratio 16:9

  # Specify API key
  %(prog)s prompts.json -o images/ --api-key YOUR_API_KEY

  # Use different model
  %(prog)s prompts.json -o images/ --model gemini-2.5-pro-image

Note: Set GEMINI_API_KEY environment variable to avoid passing API key each time.
        """
    )
    
    parser.add_argument(
        'prompts_file',
        help='Path to JSON file with character prompts'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='generated_images',
        help='Output directory for generated images (default: generated_images)'
    )
    
    parser.add_argument(
        '--aspect-ratio',
        default='1:1',
        choices=['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'],
        help='Aspect ratio for images (default: 1:1)'
    )
    
    parser.add_argument(
        '--api-key',
        default=os.getenv('GEMINI_API_KEY'),
        help='Gemini API key (default: from .env or GEMINI_API_KEY env var)'
    )
    
    parser.add_argument(
        '--model',
        default=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-image'),
        help='Model to use (default: from .env or gemini-2.5-flash-image)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay in seconds between API calls (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    # Check if prompts file exists
    if not os.path.exists(args.prompts_file):
        print(f"❌ Error: File not found: {args.prompts_file}")
        sys.exit(1)
    
    # Initialize generator
    try:
        print("🚀 Initializing Gemini Image Generator")
        generator = GeminiImageGenerator(
            api_key=args.api_key,
            model=args.model
        )
    except Exception as e:
        print(f"❌ Error initializing generator: {e}")
        sys.exit(1)
    
    # Generate images
    print(f"\n🎨 Starting image generation...")
    print(f"   Model: {args.model}")
    print(f"   Aspect ratio: {args.aspect_ratio}")
    print(f"   Delay: {args.delay}s")
    print("=" * 70)
    
    try:
        results = generator.generate_from_prompts_file(
            args.prompts_file,
            args.output_dir,
            aspect_ratio=args.aspect_ratio,
            delay_seconds=args.delay
        )
    except Exception as e:
        print(f"\n❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Export report
    report_path = os.path.join(args.output_dir, "generation_report.json")
    generator.export_generation_report(results, report_path)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 GENERATION SUMMARY")
    print("=" * 70)
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    total_time = sum(r.generation_time for r in results)
    
    print(f"Total characters: {len(results)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total time: {total_time:.1f}s")
    print(f"📁 Output directory: {args.output_dir}")
    print(f"📊 Report: {report_path}")
    
    if failed > 0:
        print("\n⚠️  Failed characters:")
        for result in results:
            if not result.success:
                print(f"  • {result.character_name}: {result.error_message}")


if __name__ == "__main__":
    main()

