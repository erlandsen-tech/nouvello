"""
Character Image Prompt Generator
Generates detailed image generation prompts for characters based on chapter analysis
Adheres to the mood, lore, and setting of the book
Designed for use with Gemini Image Generation API
"""

import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from chapter_analyzer import ChapterAnalysis
from llm_providers import MultiProviderLLM


@dataclass
class CharacterImagePrompt:
    """Image generation prompt for a character"""
    character_name: str
    image_prompt: str
    style_tags: List[str]  # Style descriptors like "gothic", "cosmic horror", etc.
    book_context: str  # Brief context about the book's setting
    chapter_references: List[str]  # Chapters where character appears
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class CharacterImagePrompter:
    """Generate image prompts for characters based on book analysis"""
    
    def __init__(self, provider: str = "bedrock", region: str = "us-east-1", 
                 model: str = None, profile: Optional[str] = None):
        """
        Initialize the prompter
        
        Args:
            provider: LLM provider (bedrock, openai)
            region: AWS region for Bedrock
            model: Specific model to use (optional)
            profile: AWS profile name (optional)
        """
        self.llm = MultiProviderLLM(provider=provider, region=region, profile=profile)
        self.model = model
    
    def generate_character_prompts(self, analyses: List[ChapterAnalysis]) -> List[CharacterImagePrompt]:
        """
        Generate image prompts for all unique characters across chapters
        
        Args:
            analyses: List of ChapterAnalysis objects
            
        Returns:
            List of CharacterImagePrompt objects
        """
        # Extract overall book context
        book_context = self._extract_book_context(analyses)
        
        # Aggregate characters across all chapters
        character_map = self._aggregate_characters(analyses)
        
        # Generate prompts for each unique character
        prompts = []
        total = len(character_map)
        
        for idx, (char_name, char_data) in enumerate(character_map.items(), 1):
            print(f"🎨 Generating prompt {idx}/{total}: {char_name}")
            
            try:
                prompt = self._generate_single_character_prompt(
                    char_name,
                    char_data,
                    book_context
                )
                prompts.append(prompt)
                print(f"   ✅ Complete")
            except Exception as e:
                print(f"   ⚠️  Error: {e}")
                # Create fallback prompt
                prompts.append(CharacterImagePrompt(
                    character_name=char_name,
                    image_prompt=f"A character named {char_name}",
                    style_tags=["literary"],
                    book_context=book_context["title"],
                    chapter_references=char_data["chapters"]
                ))
        
        return prompts
    
    def _extract_book_context(self, analyses: List[ChapterAnalysis]) -> Dict:
        """
        Extract overall book context from chapter analyses
        
        Args:
            analyses: List of ChapterAnalysis objects
            
        Returns:
            Dictionary with book context information
        """
        if not analyses:
            return {
                "title": "Unknown",
                "overall_mood": "Unknown",
                "setting_style": "Unknown",
                "genre": "Unknown"
            }
        
        # Aggregate mood and scene information
        all_moods = [a.mood_description for a in analyses if a.mood_description]
        all_scenes = [a.scene_description for a in analyses if a.scene_description]
        chapter_titles = [a.chapter_title for a in analyses]
        
        # Use LLM to synthesize overall context
        prompt = f"""Analyze these book chapters and extract overall context for character image generation.

CHAPTER TITLES:
{chr(10).join(f"- {title}" for title in chapter_titles[:10])}
{f"... and {len(chapter_titles) - 10} more chapters" if len(chapter_titles) > 10 else ""}

SAMPLE MOODS:
{chr(10).join(all_moods[:3])}

SAMPLE SCENES:
{chr(10).join(all_scenes[:3])}

Provide a JSON response with:
{{
  "title": "Inferred book title or series",
  "overall_mood": "Dominant emotional atmosphere (e.g., 'dark Gothic horror', 'cosmic dread', 'romantic adventure')",
  "setting_style": "Visual style description (e.g., '1920s New England Gothic', 'Victorian steampunk', 'ancient mythological')",
  "genre": "Primary genre(s)",
  "art_style_tags": ["tag1", "tag2", "tag3"]
}}

Focus on visual and atmospheric qualities useful for image generation.
Respond with ONLY the JSON."""

        try:
            response = self.llm.generate_response(prompt, model=self.model)
            
            # Parse JSON response
            start_idx = response.content.find('{')
            end_idx = response.content.rfind('}') + 1
            if start_idx != -1 and end_idx > 0:
                json_str = response.content[start_idx:end_idx]
                context = json.loads(json_str)
                return context
        except Exception as e:
            print(f"Warning: Failed to extract book context: {e}")
        
        # Fallback to manual extraction
        return {
            "title": chapter_titles[0] if chapter_titles else "Unknown",
            "overall_mood": "dark, mysterious",
            "setting_style": "classic literary",
            "genre": "fiction",
            "art_style_tags": ["literary", "atmospheric"]
        }
    
    def _aggregate_characters(self, analyses: List[ChapterAnalysis]) -> Dict:
        """
        Aggregate character information across all chapters
        
        Args:
            analyses: List of ChapterAnalysis objects
            
        Returns:
            Dictionary mapping character names to aggregated data
        """
        character_map = {}
        
        for analysis in analyses:
            for character in analysis.characters:
                char_name = character.get("name", "Unknown")
                
                if char_name not in character_map:
                    character_map[char_name] = {
                        "descriptions": [],
                        "chapters": [],
                        "scenes": [],
                        "moods": []
                    }
                
                # Add this occurrence
                character_map[char_name]["descriptions"].append(character.get("description", ""))
                character_map[char_name]["chapters"].append(analysis.chapter_title)
                character_map[char_name]["scenes"].append(analysis.scene_description)
                character_map[char_name]["moods"].append(analysis.mood_description)
        
        return character_map
    
    def _generate_single_character_prompt(self, char_name: str, 
                                         char_data: Dict, 
                                         book_context: Dict) -> CharacterImagePrompt:
        """
        Generate image prompt for a single character
        
        Args:
            char_name: Character name
            char_data: Aggregated character data
            book_context: Overall book context
            
        Returns:
            CharacterImagePrompt object
        """
        # Build comprehensive context for the LLM
        descriptions_text = "\n".join(f"- {desc}" for desc in char_data["descriptions"][:3])
        scenes_sample = char_data["scenes"][0] if char_data["scenes"] else "Unknown setting"
        moods_sample = char_data["moods"][0] if char_data["moods"] else "Unknown mood"
        
        prompt = f"""Generate a detailed image generation prompt for a character from a book.

CHARACTER NAME: {char_name}

CHARACTER DESCRIPTIONS FROM TEXT:
{descriptions_text}

BOOK CONTEXT:
- Title/Setting: {book_context.get('title', 'Unknown')}
- Genre: {book_context.get('genre', 'fiction')}
- Overall Mood: {book_context.get('overall_mood', 'literary')}
- Setting Style: {book_context.get('setting_style', 'classic')}
- Art Style Tags: {', '.join(book_context.get('art_style_tags', []))}

SCENE CONTEXT:
{scenes_sample[:500]}

MOOD CONTEXT:
{moods_sample[:300]}

Generate a detailed image generation prompt suitable for Gemini Image API that:
1. Captures the character's physical appearance accurately
2. Reflects the book's mood, lore, and setting
3. Includes appropriate artistic style matching the genre
4. Is detailed enough for high-quality image generation
5. Uses vivid, visual language
6. Avoids any copyrighted or trademarked references

Provide response in JSON format:
{{
  "image_prompt": "Detailed prompt for image generation (150-300 words)",
  "style_tags": ["tag1", "tag2", "tag3"],
  "key_visual_elements": ["element1", "element2", "element3"]
}}

The image_prompt should be a single, cohesive paragraph that reads naturally.
Respond with ONLY the JSON."""

        try:
            response = self.llm.generate_response(prompt, model=self.model)
            
            # Parse JSON response
            start_idx = response.content.find('{')
            end_idx = response.content.rfind('}') + 1
            
            if start_idx != -1 and end_idx > 0:
                json_str = response.content[start_idx:end_idx]
                data = json.loads(json_str)
                
                return CharacterImagePrompt(
                    character_name=char_name,
                    image_prompt=data.get("image_prompt", f"A character named {char_name}"),
                    style_tags=data.get("style_tags", []),
                    book_context=book_context.get("title", "Unknown"),
                    chapter_references=char_data["chapters"]
                )
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            print(f"Warning: Failed to parse LLM response for {char_name}: {e}")
            # Create fallback prompt from descriptions
            fallback_prompt = f"A character named {char_name}. {char_data['descriptions'][0][:200] if char_data['descriptions'] else ''}"
            return CharacterImagePrompt(
                character_name=char_name,
                image_prompt=fallback_prompt,
                style_tags=book_context.get("art_style_tags", ["literary"]),
                book_context=book_context.get("title", "Unknown"),
                chapter_references=char_data["chapters"]
            )
    
    def export_prompts(self, prompts: List[CharacterImagePrompt], 
                      output_path: str, format: str = "json"):
        """
        Export character image prompts to file
        
        Args:
            prompts: List of CharacterImagePrompt objects
            output_path: Path to output file
            format: Output format (json, markdown, text)
        """
        if format == "json":
            self._export_json(prompts, output_path)
        elif format == "markdown":
            self._export_markdown(prompts, output_path)
        elif format == "text":
            self._export_text(prompts, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        print(f"💾 Exported prompts to: {output_path}")
    
    def _export_json(self, prompts: List[CharacterImagePrompt], output_path: str):
        """Export as JSON"""
        data = [p.to_dict() for p in prompts]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _export_markdown(self, prompts: List[CharacterImagePrompt], output_path: str):
        """Export as Markdown"""
        lines = ["# Character Image Generation Prompts\n\n"]
        
        for prompt in prompts:
            lines.append(f"## {prompt.character_name}\n\n")
            lines.append(f"**Book Context:** {prompt.book_context}\n\n")
            lines.append(f"**Style Tags:** {', '.join(prompt.style_tags)}\n\n")
            lines.append(f"**Appears in Chapters:**\n")
            for chapter in prompt.chapter_references[:5]:
                lines.append(f"- {chapter}\n")
            if len(prompt.chapter_references) > 5:
                lines.append(f"- ... and {len(prompt.chapter_references) - 5} more\n")
            lines.append(f"\n### Image Generation Prompt\n\n")
            lines.append(f"{prompt.image_prompt}\n\n")
            lines.append("---\n\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def _export_text(self, prompts: List[CharacterImagePrompt], output_path: str):
        """Export as plain text"""
        lines = ["CHARACTER IMAGE GENERATION PROMPTS\n", "=" * 80 + "\n\n"]
        
        for prompt in prompts:
            lines.append(f"{prompt.character_name}\n")
            lines.append("-" * 80 + "\n")
            lines.append(f"Book: {prompt.book_context}\n")
            lines.append(f"Style: {', '.join(prompt.style_tags)}\n")
            lines.append(f"Appears in: {len(prompt.chapter_references)} chapter(s)\n\n")
            lines.append(f"IMAGE PROMPT:\n{prompt.image_prompt}\n\n")
            lines.append("=" * 80 + "\n\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def generate_from_analysis_file(self, analysis_file: str) -> List[CharacterImagePrompt]:
        """
        Convenience method to generate prompts from a saved analysis JSON file
        
        Args:
            analysis_file: Path to JSON file with chapter analyses
            
        Returns:
            List of CharacterImagePrompt objects
        """
        print(f"📖 Loading analysis from: {analysis_file}")
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert dictionaries back to ChapterAnalysis objects
        analyses = []
        for item in data:
            analysis = ChapterAnalysis(
                chapter_title=item["chapter_title"],
                chapter_number=item["chapter_number"],
                scene_description=item["scene_description"],
                mood_description=item["mood_description"],
                characters=item["characters"],
                significant_objects=item["significant_objects"],
                summary=item["summary"],
                raw_content_preview=item["raw_content_preview"]
            )
            analyses.append(analysis)
        
        print(f"✅ Loaded {len(analyses)} chapter analyses")
        
        return self.generate_character_prompts(analyses)


def main():
    """Example usage"""
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("Usage: python character_image_prompter.py <analysis_json_file>")
        print("\nExample:")
        print("  python character_image_prompter.py book_analysis.json")
        print("\nThis will generate image prompts for all characters found in the analysis.")
        return
    
    analysis_file = sys.argv[1]
    
    if not os.path.exists(analysis_file):
        print(f"❌ File not found: {analysis_file}")
        return
    
    # Initialize prompter
    print("🚀 Initializing Character Image Prompter")
    prompter = CharacterImagePrompter(provider="bedrock", region="eu-central-1")
    
    # Generate prompts
    prompts = prompter.generate_from_analysis_file(analysis_file)
    
    if not prompts:
        print("❌ No character prompts generated")
        return
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(analysis_file))[0]
    base_name = base_name.replace("_analysis", "_character_prompts")
    
    # Export as JSON
    print("\n📤 Exporting prompts...")
    prompter.export_prompts(prompts, f"{base_name}.json", format="json")
    
    # Print summary
    print(f"\n✅ Prompt generation complete!")
    print(f"   Characters processed: {len(prompts)}")
    print(f"   Output: {base_name}.json")
    
    # Print first prompt as preview
    if prompts:
        print(f"\n📋 Preview of first character prompt:")
        print("-" * 60)
        first = prompts[0]
        print(f"Character: {first.character_name}")
        print(f"Book: {first.book_context}")
        print(f"Style: {', '.join(first.style_tags)}")
        print(f"\nPrompt: {first.image_prompt[:200]}...")


if __name__ == "__main__":
    main()

