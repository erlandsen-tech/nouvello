#!/usr/bin/env .venv/bin/python
"""
Generate environment/background images for visual novels
"""
import sys
from pathlib import Path

# Add ai directory to path
sys.path.insert(0, str(Path(__file__).parent / "ai"))

from environment_image_generator import EnvironmentImageGenerator


def main():
    """Main entry point"""
    print("=" * 70)
    print("🌆 Environment Image Generator for Visual Novels")
    print("=" * 70)
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python generate_environment_images.py <book_output_dir> [--variations]")
        print()
        print("Examples:")
        print("  python generate_environment_images.py output/The_Complete_Works_of_H.P._Lovecraft")
        print("  python generate_environment_images.py output/alice --variations")
        print()
        print("Options:")
        print("  --variations    Generate multiple variations (day/night/foggy/etc.)")
        print()
        print("Available books:")
        output_dir = Path("output")
        if output_dir.exists():
            for book_dir in sorted(output_dir.iterdir()):
                if book_dir.is_dir() and (book_dir / "analysis.json").exists():
                    print(f"  - {book_dir.name}")
        print()
        sys.exit(1)
    
    book_output_dir = Path(sys.argv[1])
    generate_variations = "--variations" in sys.argv
    
    if not book_output_dir.exists():
        print(f"❌ Error: Directory not found: {book_output_dir}")
        sys.exit(1)
    
    analysis_file = book_output_dir / "analysis.json"
    if not analysis_file.exists():
        print(f"❌ Error: No analysis.json found in {book_output_dir}")
        print("Please run book analysis first!")
        sys.exit(1)
    
    # Create environments output directory
    environments_dir = book_output_dir / "environments"
    
    print(f"📖 Book: {book_output_dir.name}")
    print(f"📂 Output: {environments_dir}")
    if generate_variations:
        print("🎨 Mode: Generating variations")
    print()
    
    try:
        generator = EnvironmentImageGenerator()
        
        images = generator.generate_from_analysis(
            analysis_file,
            environments_dir,
            generate_variations=generate_variations
        )
        
        print()
        print("=" * 70)
        print("✅ Environment Generation Complete!")
        print("=" * 70)
        print(f"\nGenerated {len(images)} environment image(s):")
        for name, path in images.items():
            print(f"  📷 {name}: {path.name}")
        print()
        print(f"💡 Images saved to: {environments_dir}")
        print()
        print("Next steps:")
        print(f"  1. Review images in: {environments_dir}")
        print(f"  2. Generate visual novel: python create_visual_novel.py {book_output_dir}")
        print()
        
    except Exception as e:
        print(f"❌ Error generating environments: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

