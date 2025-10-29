"""
Chapter Analyzer - Generate Scene, Mood, Character, and Object Descriptions
Uses AWS Bedrock to analyze book chapters and extract descriptive elements
"""

import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from epub_parser import EPUBChapter, EPUBParser
from llm_providers import MultiProviderLLM, LLMResponse
from dotenv import load_dotenv


@dataclass
class ChapterAnalysis:
    """Complete analysis of a single chapter"""
    chapter_title: str
    chapter_number: int
    scene_description: str
    mood_description: str
    characters: List[Dict[str, str]]  # [{"name": "...", "description": "..."}]
    significant_objects: List[Dict[str, str]]  # [{"name": "...", "description": "..."}]
    summary: str
    raw_content_preview: str  # First 200 chars for reference
    raw_content: str  # Full original chapter content for segmentation
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class ChapterAnalyzer:
    """Analyze chapters using AWS Bedrock to extract descriptive elements"""
    
    def __init__(self, region: str = "eu-central-1", model: str = None, profile: Optional[str] = None):
        """
        Initialize the analyzer
        
        Args:
            region: AWS region for Bedrock
            model: Specific model to use (optional, uses default if not specified)
            profile: AWS profile name (optional)
        """
        load_dotenv()
        self.llm = MultiProviderLLM(provider="bedrock", region=region, profile=profile)
        # Default to faster model unless overridden
        self.model = model or os.getenv("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
        
    def analyze_chapter(self, chapter: EPUBChapter) -> ChapterAnalysis:
        """
        Analyze a single chapter and extract all descriptive elements
        
        Args:
            chapter: EPUBChapter object to analyze
            
        Returns:
            ChapterAnalysis object with all extracted elements
        """
        prompt = self._build_analysis_prompt(chapter.title, chapter.content)
        
        try:
            response = self.llm.generate_response(prompt, model=self.model)
            analysis_data = self._parse_response(response.content)
            
            return ChapterAnalysis(
                chapter_title=chapter.title,
                chapter_number=chapter.order + 1,
                scene_description=analysis_data.get("scene", ""),
                mood_description=analysis_data.get("mood", ""),
                characters=analysis_data.get("characters", []),
                significant_objects=analysis_data.get("objects", []),
                summary=analysis_data.get("summary", ""),
                raw_content_preview=chapter.content[:200],
                raw_content=chapter.content
            )
            
        except Exception as e:
            print(f"Error analyzing chapter '{chapter.title}': {e}")
            # Return empty analysis on error
            return ChapterAnalysis(
                chapter_title=chapter.title,
                chapter_number=chapter.order + 1,
                scene_description="Error during analysis",
                mood_description="Error during analysis",
                characters=[],
                significant_objects=[],
                summary="Error during analysis",
                raw_content_preview=chapter.content[:200],
                raw_content=chapter.content
            )
    
    def analyze_chapters(self, chapters: List[EPUBChapter], 
                        selected_indices: Optional[List[int]] = None) -> List[ChapterAnalysis]:
        """
        Analyze multiple chapters
        
        Args:
            chapters: List of EPUBChapter objects
            selected_indices: Optional list of chapter indices to analyze (0-based)
                            If None, analyzes all chapters
                            
        Returns:
            List of ChapterAnalysis objects
        """
        if selected_indices is None:
            chapters_to_analyze = chapters
        else:
            chapters_to_analyze = [chapters[i] for i in selected_indices if 0 <= i < len(chapters)]
        
        # Filter out non-story chapters (contents, acknowledgements, etc.)
        chapters_to_analyze = [ch for ch in chapters_to_analyze if not _should_skip_chapter(ch.title, ch.content)]
        
        if not chapters_to_analyze:
            print("⚠️  All selected chapters were skipped (non-story content)")
            return []
        
        # Get number of workers from env (default to 4)
        num_workers = int(os.getenv("ANALYSIS_WORKERS", "4"))
        
        # Use parallel processing if multiple chapters
        if len(chapters_to_analyze) > 1 and num_workers > 1:
            # Don't create more workers than chapters
            actual_workers = min(num_workers, len(chapters_to_analyze))
            print(f"🚀 Running parallel analysis with {actual_workers} workers")
            return self._analyze_chapters_parallel(chapters_to_analyze, actual_workers)
        else:
            # Sequential for single chapter or single worker
            analyses = []
            total = len(chapters_to_analyze)
            
            for idx, chapter in enumerate(chapters_to_analyze, 1):
                print(f"📖 Analyzing chapter {idx}/{total}: {chapter.title}")
                analysis = self.analyze_chapter(chapter)
                analyses.append(analysis)
                print(f"   ✅ Complete")
            
            return analyses
    
    def _analyze_chapters_parallel(self, chapters: List[EPUBChapter], num_workers: int) -> List[ChapterAnalysis]:
        """Analyze multiple chapters in parallel using processes (signal-safe)."""
        analyses: List[ChapterAnalysis] = []

        # Convert EPUBChapter objects to dicts for pickling
        chapter_dicts = [{'title': ch.title, 'content': ch.content, 'order': ch.order} for ch in chapters]
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_chapter = {executor.submit(_analyze_chapter_worker, ch_data): ch_data for ch_data in chapter_dicts}
            
            for future in as_completed(future_to_chapter):
                ch_data = future_to_chapter[future]
                try:
                    analysis = future.result()
                    analyses.append(analysis)
                except Exception as e:
                    print(f"   ❌ Error analyzing {ch_data['title']}: {e}")
                    analyses.append(ChapterAnalysis(
                        chapter_title=ch_data['title'],
                        chapter_number=ch_data['order'] + 1,
                        scene_description="Error during analysis",
                        mood_description="Error during analysis",
                        characters=[],
                        significant_objects=[],
                        summary="Error during analysis",
                        raw_content_preview=ch_data['content'][:200] if ch_data.get('content') else "",
                        raw_content=ch_data.get('content', '')
                    ))

        analyses.sort(key=lambda a: a.chapter_number)
        return analyses
    
    def _build_analysis_prompt(self, title: str, content: str) -> str:
        """
        Build the prompt for chapter analysis
        
        Args:
            title: Chapter title
            content: Chapter content
            
        Returns:
            Formatted prompt string
        """
        # Truncate content if too long (keep first ~8000 chars to stay within token limits)
        max_content_length = 8000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n[... content truncated for analysis ...]"
        
        prompt = f"""You are a literary analyst. Analyze the following book chapter and extract key descriptive elements.

CHAPTER TITLE: {title}

CHAPTER CONTENT:
{content}

Please provide a detailed analysis in the following JSON format:

{{
  "scene": "Detailed description of the physical setting, location, time of day, weather, atmosphere, and spatial layout. Be vivid and specific.",
  "mood": "Description of the emotional atmosphere, tone, tension level, and overall feeling the chapter evokes. Include pacing and narrative energy.",
  "characters": [
    {{
      "name": "Character name",
      "description": "Physical appearance, personality traits, emotional state, role in this chapter, relationships"
    }}
  ],
  "objects": [
    {{
      "name": "Object name",
      "description": "Detailed description including appearance, significance, symbolism, how it's used"
    }}
  ],
  "summary": "Concise summary of the key events, plot developments, and important moments in this chapter"
}}

IMPORTANT INSTRUCTIONS:
1. Be specific and detailed in all descriptions
2. Include ALL significant characters that appear or are mentioned
3. Only include objects that are actually significant to the plot, symbolism, or character development
4. Keep the summary to 2-3 sentences focusing on key events
5. If a field has no relevant content, use an empty string or empty array
6. Ensure your response is valid JSON that can be parsed
7. Do not include any text outside the JSON structure

Respond with ONLY the JSON, no additional text or explanation."""

        return prompt
    
    def _parse_response(self, response_content: str) -> Dict:
        """
        Parse LLM response and extract structured data
        
        Args:
            response_content: Raw response from LLM
            
        Returns:
            Dictionary with extracted analysis data
        """
        try:
            # Try to find JSON in the response
            # Sometimes LLM adds text before/after JSON
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_content[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Validate and normalize structure
            return {
                "scene": data.get("scene", ""),
                "mood": data.get("mood", ""),
                "characters": data.get("characters", []),
                "objects": data.get("objects", []),
                "summary": data.get("summary", "")
            }
            
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON response: {e}")
            print(f"Raw response: {response_content[:500]}")
            return {
                "scene": "",
                "mood": "",
                "characters": [],
                "objects": [],
                "summary": response_content[:500]  # Use raw text as summary fallback
            }
        except Exception as e:
            print(f"Warning: Error parsing response: {e}")
            return {
                "scene": "",
                "mood": "",
                "characters": [],
                "objects": [],
                "summary": ""
            }
    
    def analyze_epub(self, epub_path: str, 
                    selected_chapters: Optional[List[int]] = None) -> List[ChapterAnalysis]:
        """
        Convenience method to parse EPUB and analyze chapters in one go
        
        Args:
            epub_path: Path to EPUB file
            selected_chapters: Optional list of chapter indices to analyze (0-based)
            
        Returns:
            List of ChapterAnalysis objects
        """
        print(f"📚 Parsing EPUB: {epub_path}")
        parser = EPUBParser(epub_path)
        chapters = parser.parse()
        
        if not chapters:
            print("❌ No chapters found in EPUB")
            return []
        
        print(f"✅ Found {len(chapters)} chapters")
        
        if selected_chapters:
            print(f"🎯 Analyzing selected chapters: {selected_chapters}")
        else:
            print(f"🎯 Analyzing all chapters")
        
        return self.analyze_chapters(chapters, selected_chapters)
    
    def export_analyses(self, analyses: List[ChapterAnalysis], 
                       output_path: str, format: str = "json"):
        """
        Export analyses to file
        
        Args:
            analyses: List of ChapterAnalysis objects
            output_path: Path to output file
            format: Output format (json, markdown, text)
        """
        if format == "json":
            self._export_json(analyses, output_path)
        elif format == "markdown":
            self._export_markdown(analyses, output_path)
        elif format == "text":
            self._export_text(analyses, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        print(f"💾 Exported analyses to: {output_path}")
    
    def _export_json(self, analyses: List[ChapterAnalysis], output_path: str):
        """Export as JSON"""
        data = [a.to_dict() for a in analyses]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _export_markdown(self, analyses: List[ChapterAnalysis], output_path: str):
        """Export as Markdown"""
        lines = ["# Chapter Analyses\n"]
        
        for analysis in analyses:
            lines.append(f"## {analysis.chapter_title}\n")
            lines.append(f"**Chapter Number:** {analysis.chapter_number}\n")
            lines.append(f"### Scene\n{analysis.scene_description}\n")
            lines.append(f"### Mood\n{analysis.mood_description}\n")
            
            lines.append(f"### Characters\n")
            for char in analysis.characters:
                lines.append(f"- **{char.get('name', 'Unknown')}**: {char.get('description', '')}\n")
            
            lines.append(f"### Significant Objects\n")
            for obj in analysis.significant_objects:
                lines.append(f"- **{obj.get('name', 'Unknown')}**: {obj.get('description', '')}\n")
            
            lines.append(f"### Summary\n{analysis.summary}\n")
            lines.append("\n---\n\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def _export_text(self, analyses: List[ChapterAnalysis], output_path: str):
        """Export as plain text"""
        lines = ["CHAPTER ANALYSES\n" + "=" * 80 + "\n\n"]
        
        for analysis in analyses:
            lines.append(f"{analysis.chapter_title}\n")
            lines.append(f"Chapter {analysis.chapter_number}\n")
            lines.append("-" * 80 + "\n\n")
            
            lines.append(f"SCENE:\n{analysis.scene_description}\n\n")
            lines.append(f"MOOD:\n{analysis.mood_description}\n\n")
            
            lines.append("CHARACTERS:\n")
            for char in analysis.characters:
                lines.append(f"  • {char.get('name', 'Unknown')}\n")
                lines.append(f"    {char.get('description', '')}\n\n")
            
            lines.append("SIGNIFICANT OBJECTS:\n")
            for obj in analysis.significant_objects:
                lines.append(f"  • {obj.get('name', 'Unknown')}\n")
                lines.append(f"    {obj.get('description', '')}\n\n")
            
            lines.append(f"SUMMARY:\n{analysis.summary}\n\n")
            lines.append("=" * 80 + "\n\n")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)


def main():
    """Example usage and testing"""
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("Usage: python chapter_analyzer.py <epub_file> [chapter_indices]")
        print("\nExample:")
        print("  python chapter_analyzer.py book.epub              # Analyze all chapters")
        print("  python chapter_analyzer.py book.epub 0,1,2        # Analyze chapters 0, 1, 2")
        print("  python chapter_analyzer.py book.epub 0-5          # Analyze chapters 0 through 5")
        return
    
    epub_path = sys.argv[1]
    
    # Parse chapter selection
    selected_chapters = None
    if len(sys.argv) >= 3:
        chapter_spec = sys.argv[2]
        if '-' in chapter_spec:
            # Range: 0-5
            start, end = map(int, chapter_spec.split('-'))
            selected_chapters = list(range(start, end + 1))
        else:
            # List: 0,1,2
            selected_chapters = [int(x.strip()) for x in chapter_spec.split(',')]
    
    # Initialize analyzer
    print("🚀 Initializing Chapter Analyzer with AWS Bedrock")
    analyzer = ChapterAnalyzer(region="eu-central-1")
    
    # Analyze chapters
    analyses = analyzer.analyze_epub(epub_path, selected_chapters)
    
    if not analyses:
        print("❌ No analyses generated")
        return
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(epub_path))[0]
    
    # Export as JSON
    print("\n📤 Exporting results...")
    analyzer.export_analyses(analyses, f"{base_name}_analysis.json", format="json")
    
    # Print summary
    print(f"\n✅ Analysis complete!")
    print(f"   Chapters analyzed: {len(analyses)}")
    print(f"   Output: {base_name}_analysis.json")
    
    # Print first analysis as preview
    if analyses:
        print(f"\n📋 Preview of first chapter analysis:")
        print("-" * 60)
        first = analyses[0]
        print(f"Title: {first.chapter_title}")
        print(f"Scene: {first.scene_description[:150]}...")
        print(f"Characters: {len(first.characters)} found")
        print(f"Objects: {len(first.significant_objects)} found")


def _analyze_chapter_worker(chapter_data: dict) -> ChapterAnalysis:
    """Worker function for parallel analysis (must be at module level for pickling)"""
    # Re-create analyzer in the subprocess
    local_analyzer = ChapterAnalyzer(region=os.getenv("AWS_REGION", "eu-central-1"),
                                     model=os.getenv("BEDROCK_MODEL"))
    
    # Create temporary EPUBChapter object
    class TempChapter:
        def __init__(self, data):
            self.title = data['title']
            self.content = data['content']
            self.order = data['order']
    
    temp_chapter = TempChapter(chapter_data)
    return local_analyzer.analyze_chapter(temp_chapter)


def _should_skip_chapter(chapter_title: str, chapter_content: str) -> bool:
    """Check if a chapter should be skipped (non-story content)"""
    title_lower = chapter_title.lower()
    content_lower = chapter_content.lower()[:500]  # Check first 500 chars
    
    skip_keywords = [
        'contents', 'table of contents', 'toc',
        'acknowledgements', 'acknowledgments',
        'preface', 'foreword', 'introduction',
        'copyright', 'license', 'project gutenberg',
        'the millennium fulcrum edition',
        'credits', 'about', 'colophon'
    ]
    
    # Check title
    for keyword in skip_keywords:
        if keyword in title_lower:
            return True
    
    # Check if content is too short or looks like metadata
    if len(chapter_content.strip()) < 100:
        return True
    
    # Check if it's mostly metadata/tags
    if '<html' in content_lower or '<?xml' in content_lower:
        return True
    
    return False


if __name__ == "__main__":
    main()

