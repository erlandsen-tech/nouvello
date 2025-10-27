"""
Enhanced Ren'Py script generator with better narrative parsing
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from json_to_renpy import RenpyScriptGenerator


class EnhancedScriptGenerator(RenpyScriptGenerator):
    """Enhanced version with better dialogue and narration parsing"""
    
    def parse_dialogue_line(self, text: str) -> Tuple[str, str, str]:
        """
        Parse a line to extract speaker, dialogue, and remaining narration
        
        Returns: (speaker_name, dialogue_text, narration_text)
        """
        # Pattern for dialogue with speaker
        patterns = [
            # "Name," said X, "dialogue"
            r'"([^"]+)," ([^,]+), "([^"]+)"',
            # "Name said, "dialogue"
            r'([^,]+) said, "([^"]+)"',
            # "dialogue," said Name
            r'"([^"]+)," said ([^.]+)\.',
            # "dialogue," Name exclaimed/shouted/etc
            r'"([^"]+)," ([^\s]+) (exclaimed|shouted|cried|responded|replied|continued|announced)',
            # Simple: "dialogue"
            r'"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 1:
                    # Simple dialogue, no speaker
                    return ("", groups[0], text.replace(match.group(0), "").strip())
                elif len(groups) == 2:
                    # Speaker and dialogue
                    dialogue = groups[0] if groups[0].count('"') == 0 else groups[1]
                    speaker = groups[1] if dialogue == groups[0] else groups[0]
                    return (speaker, dialogue, text.replace(match.group(0), "").strip())
                elif len(groups) == 3:
                    # More complex pattern
                    return (groups[1], groups[0] + " " + groups[2], text.replace(match.group(0), "").strip())
        
        return ("", "", text)
    
    def parse_chapter_content(self, content: str, characters: List[Dict]) -> List[Dict[str, str]]:
        """
        Parse chapter content into a sequence of narration and dialogue segments
        """
        segments = []
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        
        # Build character name map (including partial names)
        char_names = {char["name"]: self.sanitize_name(char["name"]) for char in characters}
        char_names_lower = {name.lower(): char_id for name, char_id in char_names.items()}
        
        # Also map partial names (e.g., "Bugs" -> "old_bugs")
        char_partial_map = {}
        for name, char_id in char_names.items():
            words = name.split()
            for word in words:
                if len(word) > 3:  # Avoid common words
                    char_partial_map[word.lower()] = char_id
        
        for para in paragraphs:
            # Skip chapter headers and separators
            if para.startswith("Chapter ") or para.startswith("=====") or para.startswith("("):
                continue
            
            # Check if any character is mentioned in this paragraph
            mentioned_char = None
            para_lower = para.lower()
            # Check full names first
            for name, char_id in char_names_lower.items():
                if name in para_lower:
                    mentioned_char = char_id
                    break
            # Then check partial names if no full name found
            if not mentioned_char:
                for partial, char_id in char_partial_map.items():
                    if partial in para_lower:
                        mentioned_char = char_id
                        break
            
            # Add mention info to segment
            segment_extra = {"mentioned_character": mentioned_char} if mentioned_char else {}
            
            # Check if paragraph contains dialogue
            if '"' in para:
                # Try to parse dialogue
                speaker_name, dialogue, narration = self.parse_dialogue_line(para)
                
                # Find matching character ID
                speaker_id = None
                if speaker_name:
                    speaker_lower = speaker_name.lower()
                    # Direct match
                    if speaker_lower in char_names_lower:
                        speaker_id = char_names_lower[speaker_lower]
                    else:
                        # Partial match (e.g., "Schultz" matches "Pete Schultz")
                        for char_full, char_id in char_names_lower.items():
                            if speaker_lower in char_full or char_full in speaker_lower:
                                speaker_id = char_id
                                break
                
                # Add narration before dialogue if present
                if narration and len(narration) > 10:
                    segments.append({"type": "narration", "text": narration})
                
                # Add dialogue
                if dialogue:
                    if speaker_id:
                        segments.append({
                            "type": "dialogue",
                            "speaker": speaker_id,
                            "text": dialogue,
                            **segment_extra
                        })
                    else:
                        # Unattributed dialogue - treat as narration
                        segments.append({"type": "narration", "text": f'"{dialogue}"', **segment_extra})
            else:
                # Pure narration
                segments.append({"type": "narration", "text": para, **segment_extra})
        
        return segments
    
    def generate_enhanced_chapter_script(self, 
                                        chapter_data: Dict[str, Any],
                                        chapter_content: str = None,
                                        max_segments: int = 150) -> str:
        """Generate an enhanced Ren'Py script with better dialogue handling"""
        lines = []
        
        chapter_title = chapter_data.get("chapter_title", "Untitled")
        chapter_num = chapter_data.get("chapter_number", 0)
        scene_desc = chapter_data.get("scene_description", "")
        mood_desc = chapter_data.get("mood_description", "")
        characters = chapter_data.get("characters", [])
        
        # Generate label
        chapter_label = f"chapter_{chapter_num}_{self.sanitize_name(chapter_title)}"
        
        lines.append(f"label {chapter_label}:")
        lines.append(f'    # Chapter {chapter_num}: {chapter_title}')
        lines.append("")
        
        # Set scene - use generated background if available
        lines.append("    # Scene setup")
        # Try to use a generated background based on chapter name
        scene_label = self.sanitize_name(chapter_title)
        lines.append(f'    # scene bg {scene_label} with fade  # Use this if environment image exists')
        lines.append('    scene bg default with fade')
        lines.append('    # play music "audio/bgm.mp3" fadein 2.0  # Add music here')
        lines.append("")
        
        # Opening narration about setting
        if scene_desc:
            lines.append("    # Scene description")
            # Combine into 4-5 sentence blocks instead of line-by-line
            sentences = scene_desc.split('. ')
            current_block = []
            for i, sentence in enumerate(sentences[:10]):
                current_block.append(sentence.strip())
                # Every 4-5 sentences, create a block
                if len(current_block) >= 4 or i == len(sentences) - 1:
                    block_text = '. '.join(current_block)
                    if not block_text.endswith('.'):
                        block_text += '.'
                    lines.append(f'    "{block_text}"')
                    lines.append("")
                    current_block = []
            if current_block:  # Add any remaining
                block_text = '. '.join(current_block)
                if not block_text.endswith('.'):
                    block_text += '.'
                lines.append(f'    "{block_text}"')
            lines.append("")
        
        # Track which characters have been introduced
        introduced_chars = set()
        current_char = None
        
        # Parse and add chapter content
        if chapter_content:
            lines.append("    # Story begins")
            segments = self.parse_chapter_content(chapter_content, characters)
            
            for i, segment in enumerate(segments[:max_segments]):
                seg_type = segment["type"]
                text = segment["text"]
                
                # Skip very short segments
                if len(text) < 5:
                    continue
                
                # Check if a character is mentioned
                mentioned = segment.get("mentioned_character")
                
                if seg_type == "dialogue":
                    speaker = segment["speaker"]
                    
                    # Switch to speaker if different from current
                    if speaker and speaker != current_char:
                        if current_char:
                            lines.append(f'    hide {current_char} with dissolve')
                        lines.append(f'    show {speaker} neutral at center with dissolve')
                        introduced_chars.add(speaker)
                        current_char = speaker
                    
                    # Keep dialogue as single block
                    lines.append(f'    {speaker} "{text}"')
                else:
                    # Narration - switch to mentioned character if different
                    if mentioned and mentioned != current_char:
                        if current_char:
                            lines.append(f'    hide {current_char} with dissolve')
                        lines.append(f'    show {mentioned} neutral at center with dissolve')
                        introduced_chars.add(mentioned)
                        current_char = mentioned
                    
                    # Keep as complete paragraph
                    lines.append(f'    "{text}"')
                
                lines.append("")
        else:
            # Fallback: use character descriptions
            lines.append("    # Character introductions")
            for char in characters[:3]:
                name = char.get("name", "Unknown")
                char_id = self.sanitize_name(name)
                description = char.get("description", "")
                
                lines.append(f'    show {char_id} neutral at center with dissolve')
                
                intro = description.split(".")[0] + "." if "." in description else description[:150]
                wrapped_lines = self.wrap_dialogue(intro, 70)
                for wrapped_line in wrapped_lines:
                    lines.append(f'    "{wrapped_line}"')
                lines.append("")
        
        # End of chapter
        lines.append("    # End of chapter")
        lines.append('    scene black with fade')
        lines.append('    "To be continued..."')
        lines.append("    return")
        lines.append("")
        
        return "\n".join(lines)
    
    def convert_book_to_renpy(self, 
                             book_analysis_path: Path,
                             chapter_dir: Path,
                             output_game_dir: Path) -> Dict[str, Path]:
        """Convert with enhanced parsing"""
        # Load book analysis
        with open(book_analysis_path) as f:
            book_data = json.load(f)
        
        if isinstance(book_data, list) and len(book_data) > 0:
            book_data = book_data[0]
        
        book_title = book_data.get("chapter_title", "Unknown Book")
        characters = book_data.get("characters", [])
        
        # Create game directory
        game_dir = Path(output_game_dir) / "game"
        game_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        # Generate character definitions
        char_defs = self.generate_character_definitions(characters)
        char_file = game_dir / "characters.rpy"
        with open(char_file, "w") as f:
            f.write(char_defs)
        generated_files["characters"] = char_file
        
        # Load chapter content
        chapter_content = None
        content_file = chapter_dir / "content.txt"
        if content_file.exists():
            with open(content_file) as f:
                chapter_content = f.read()
        
        # Generate enhanced chapter script
        chapter_script = self.generate_enhanced_chapter_script(book_data, chapter_content)
        chapter_file = game_dir / "chapter.rpy"
        with open(chapter_file, "w") as f:
            f.write(chapter_script)
        generated_files["chapters"] = [chapter_file]
        
        # Generate main script
        main_script = self.generate_main_script(book_title, [book_data])
        script_file = game_dir / "script.rpy"
        with open(script_file, "w") as f:
            f.write(main_script)
        generated_files["main_script"] = script_file
        
        # Create audio directory (but don't create placeholder files)
        audio_dir = game_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        
        return generated_files


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python enhanced_script_generator.py <book_analysis.json> <chapter_dir> <output_dir>")
        sys.exit(1)
    
    book_analysis = Path(sys.argv[1])
    chapter_dir = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    
    generator = EnhancedScriptGenerator(output_dir)
    files = generator.convert_book_to_renpy(book_analysis, chapter_dir, output_dir)
    
    print("Generated files:")
    for key, value in files.items():
        if isinstance(value, list):
            for v in value:
                print(f"  {key}: {v}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()

