#!/usr/bin/env python3
"""
Demo: Character Image Generation from Existing Analysis
Shows how to use the character image generation system
"""

import os
import sys
from character_image_prompter import CharacterImagePrompter

def main():
    """Demo the character image prompt generation"""
    
    # This demo uses an existing analysis file
    # You can generate one using analyze_chapters.py first
    
    print("=" * 70)
    print("🎨 DEMO: Character Image Prompt Generation")
    print("=" * 70)
    
    # Check for analysis file
    analysis_files = [
        "../The_Complete_Works_of_H.P._Lovecraft_analysis.json",
        "The_Complete_Works_of_H.P._Lovecraft_analysis.json",
    ]
    
    analysis_file = None
    for path in analysis_files:
        if os.path.exists(path):
            analysis_file = path
            break
    
    if not analysis_file:
        print("\n❌ No analysis file found.")
        print("\nTo use this demo:")
        print("  1. First analyze an EPUB:")
        print("     python ../analyze_chapters.py books/your_book.epub -c 0-5")
        print("\n  2. Then run this demo:")
        print("     python demo_image_generation.py")
        return
    
    print(f"\n📖 Using analysis file: {analysis_file}")
    
    # Initialize prompter
    print("\n🚀 Initializing Character Image Prompter...")
    prompter = CharacterImagePrompter(
        provider="bedrock",
        region="eu-central-1"
    )
    
    # Generate prompts
    print("\n🎨 Generating character image prompts...")
    prompts = prompter.generate_from_analysis_file(analysis_file)
    
    if not prompts:
        print("❌ No character prompts generated")
        return
    
    # Show results
    print("\n" + "=" * 70)
    print("✅ GENERATED PROMPTS")
    print("=" * 70)
    
    for idx, prompt in enumerate(prompts[:3], 1):  # Show first 3
        print(f"\n{idx}. {prompt.character_name}")
        print(f"   Book: {prompt.book_context}")
        print(f"   Style: {', '.join(prompt.style_tags)}")
        print(f"   Appears in: {len(prompt.chapter_references)} chapter(s)")
        print(f"\n   Prompt:")
        print(f"   {prompt.image_prompt[:200]}...")
        print()
    
    if len(prompts) > 3:
        print(f"\n... and {len(prompts) - 3} more characters")
    
    # Export
    print("\n📤 Exporting prompts...")
    output_dir = "../output_demo"
    os.makedirs(output_dir, exist_ok=True)
    
    prompter.export_prompts(
        prompts,
        os.path.join(output_dir, "demo_character_prompts.json"),
        format="json"
    )
    prompter.export_prompts(
        prompts,
        os.path.join(output_dir, "demo_character_prompts.md"),
        format="markdown"
    )
    
    print(f"   ✅ JSON: {output_dir}/demo_character_prompts.json")
    print(f"   ✅ Markdown: {output_dir}/demo_character_prompts.md")
    
    print("\n" + "=" * 70)
    print("💡 NEXT STEPS")
    print("=" * 70)
    print("\nTo generate images with Gemini API:")
    print(f"  export GEMINI_API_KEY='your-api-key'")
    print(f"  python gemini_image_generator.py {output_dir}/demo_character_prompts.json -o {output_dir}/images")
    print("\nOr use the complete workflow:")
    print(f"  python ../generate_character_images.py --analysis {analysis_file} --gemini-key YOUR_KEY")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

