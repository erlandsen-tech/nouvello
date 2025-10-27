"""
Expression Image Generator
Generates character expression variations from base images using Gemini image editing
"""

import os
import json
import time
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass
from PIL import Image
from io import BytesIO
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
class GeneratedExpression:
    """Represents a generated expression image"""
    character_name: str
    expression: str
    base_image_path: str
    output_path: str
    generation_time: float = 0.0
    success: bool = True
    error_message: str = ""


class ExpressionImageGenerator:
    """Generate expression variations using Gemini image editing"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the generator
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY from .env)
            model: Model to use (defaults to GEMINI_MODEL from .env or gemini-2.5-flash-image)
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai package not installed. Install with: pip install google-genai")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set GEMINI_API_KEY in .env file or pass api_key parameter")
        
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-image")
        self.client = genai.Client(api_key=self.api_key)
    
    def generate_expression_image(self, character_name: str, expression: str,
                                  base_image_path: str, prompt: str,
                                  output_dir: str, aspect_ratio: str = "1:1") -> GeneratedExpression:
        """
        Generate a single expression variation
        
        Args:
            character_name: Name of the character
            expression: Expression name (e.g., "happy", "sad")
            base_image_path: Path to base character image
            prompt: Editing prompt for the expression
            output_dir: Directory to save generated image
            aspect_ratio: Aspect ratio for output image
            
        Returns:
            GeneratedExpression object with results
        """
        start_time = time.time()
        
        # Create output filename
        safe_name = self._sanitize_filename(character_name)
        output_path = os.path.join(output_dir, f"{safe_name}_{expression}.png")
        
        try:
            print(f"  🎭 Generating: {expression}")
            
            # Load base image
            base_image = Image.open(base_image_path)
            
            # Generate edited image with Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, base_image],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )
            )
            
            # Extract and save image
            image_saved = False
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(f"     ℹ️  Model response: {part.text[:100]}")
                elif part.inline_data is not None:
                    image = Image.open(BytesIO(part.inline_data.data))
                    image.save(output_path)
                    image_saved = True
                    print(f"     ✅ Saved: {expression}.png")
            
            if not image_saved:
                raise ValueError("No image data in response")
            
            generation_time = time.time() - start_time
            
            return GeneratedExpression(
                character_name=character_name,
                expression=expression,
                base_image_path=base_image_path,
                output_path=output_path,
                generation_time=generation_time,
                success=True
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            print(f"     ❌ Error: {str(e)}")
            
            return GeneratedExpression(
                character_name=character_name,
                expression=expression,
                base_image_path=base_image_path,
                output_path="",
                generation_time=generation_time,
                success=False,
                error_message=str(e)
            )
    
    def generate_character_expressions(self, character_name: str,
                                       base_image_path: str,
                                       expressions_file: str,
                                       output_dir: str,
                                       aspect_ratio: str = "1:1",
                                       delay_seconds: float = 1.0) -> List[GeneratedExpression]:
        """
        Generate all expression variations for a character
        
        Args:
            character_name: Name of the character
            base_image_path: Path to base character image
            expressions_file: Path to expressions.json file
            output_dir: Directory to save generated images
            aspect_ratio: Aspect ratio for images
            delay_seconds: Delay between API calls
            
        Returns:
            List of GeneratedExpression objects
        """
        print(f"\n📖 Loading expressions from: {expressions_file}")
        
        with open(expressions_file, 'r', encoding='utf-8') as f:
            expressions = json.load(f)
        
        print(f"✅ Loaded {len(expressions)} expressions for {character_name}")
        
        if not os.path.exists(base_image_path):
            print(f"❌ Error: Base image not found: {base_image_path}")
            return []
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate each expression
        results = []
        total = len(expressions)
        
        for idx, expr_data in enumerate(expressions, 1):
            expression = expr_data.get("expression", f"expr_{idx}")
            prompt = expr_data.get("editing_prompt", "")
            
            print(f"\n[{idx}/{total}] Expression: {expression}")
            
            result = self.generate_expression_image(
                character_name,
                expression,
                base_image_path,
                prompt,
                output_dir,
                aspect_ratio
            )
            results.append(result)
            
            # Delay between requests
            if idx < total and delay_seconds > 0:
                time.sleep(delay_seconds)
        
        return results
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize character name for filename"""
        import re
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = re.sub(r'\s+', '_', name)
        return name.strip('_')
    
    def export_generation_report(self, results: List[GeneratedExpression], output_path: str):
        """Export generation results to report"""
        report = {
            "total_expressions": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_time_seconds": sum(r.generation_time for r in results),
            "results": [
                {
                    "character_name": r.character_name,
                    "expression": r.expression,
                    "base_image": r.base_image_path,
                    "output_path": r.output_path,
                    "generation_time": round(r.generation_time, 2),
                    "success": r.success,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 Generation report saved: {output_path}")


def main():
    """Command-line interface"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate character expression images using Gemini image editing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate expressions for a single character
  %(prog)s \\
    --base-image output/Book/images/Old_Bugs.png \\
    --expressions test_prompts/Old_Bugs/expressions.json \\
    -o output/Book/images/expressions/

  # Specify API key and aspect ratio
  %(prog)s \\
    --base-image output/Book/images/Character.png \\
    --expressions prompts/Character/expressions.json \\
    -o output_expressions/ \\
    --aspect-ratio 3:4 \\
    --api-key YOUR_KEY

Note: Set GEMINI_API_KEY in .env to avoid passing API key each time.
        """
    )
    
    parser.add_argument(
        '--base-image',
        required=True,
        help='Path to base character image'
    )
    
    parser.add_argument(
        '--expressions',
        required=True,
        help='Path to expressions.json file'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='expression_images',
        help='Output directory for generated images (default: expression_images)'
    )
    
    parser.add_argument(
        '--character-name',
        help='Character name (auto-detected from paths if not provided)'
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
        help='Gemini API key (default: from .env)'
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
    
    # Auto-detect character name if not provided
    if not args.character_name:
        # Try to extract from expressions path
        parts = Path(args.expressions).parts
        if len(parts) >= 2:
            args.character_name = parts[-2]
        else:
            args.character_name = "Character"
    
    # Check files exist
    if not os.path.exists(args.base_image):
        print(f"❌ Error: Base image not found: {args.base_image}")
        sys.exit(1)
    
    if not os.path.exists(args.expressions):
        print(f"❌ Error: Expressions file not found: {args.expressions}")
        sys.exit(1)
    
    # Initialize generator
    try:
        print("🚀 Initializing Expression Image Generator")
        generator = ExpressionImageGenerator(
            api_key=args.api_key,
            model=args.model
        )
    except Exception as e:
        print(f"❌ Error initializing generator: {e}")
        sys.exit(1)
    
    # Generate expressions
    print(f"\n🎭 Generating expression variations...")
    print(f"   Character: {args.character_name}")
    print(f"   Base image: {args.base_image}")
    print(f"   Model: {args.model}")
    print(f"   Aspect ratio: {args.aspect_ratio}")
    print("=" * 70)
    
    try:
        results = generator.generate_character_expressions(
            args.character_name,
            args.base_image,
            args.expressions,
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
    report_path = os.path.join(args.output_dir, f"{args.character_name}_expressions_report.json")
    generator.export_generation_report(results, report_path)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 GENERATION SUMMARY")
    print("=" * 70)
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    total_time = sum(r.generation_time for r in results)
    
    print(f"Character: {args.character_name}")
    print(f"Total expressions: {len(results)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total time: {total_time:.1f}s")
    print(f"📁 Output directory: {args.output_dir}")
    print(f"📊 Report: {report_path}")
    
    if failed > 0:
        print("\n⚠️  Failed expressions:")
        for result in results:
            if not result.success:
                print(f"  • {result.expression}: {result.error_message}")


if __name__ == "__main__":
    main()

