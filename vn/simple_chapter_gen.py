"""
Simple chapter generator that shows character sprites at key story moments
"""
from pathlib import Path
import re
from json_to_renpy import RenpyScriptGenerator


def create_simple_illustrated_chapter(analysis_file: Path, content_file: Path, output_file: Path):
    """Create a chapter script that shows characters at key moments"""
    
    import json
    
    # Load analysis
    with open(analysis_file) as f:
        data = json.load(f)
        if isinstance(data, list):
            data = data[0]
    
    # Load content
    with open(content_file) as f:
        content = f.read()
    
    gen = RenpyScriptGenerator(output_file.parent)
    
    chapter_title = data.get("chapter_title", "Chapter")
    chapter_num = data.get("chapter_number", 1)
    characters = data.get("characters", [])
    scene_desc = data.get("scene_description", "")
    
    # Build character name map (prioritize full names first)
    char_map = []  # List of (search_term, char_id, priority) tuples
    for char in characters:
        name = char.get("name", "")
        char_id = gen.sanitize_name(name)
        # Full name gets highest priority
        char_map.append((name.lower(), char_id, 10))
        # Individual words get lower priority
        words = name.split()
        if len(words) > 1:
            for word in words:
                if len(word) > 3:
                    char_map.append((word.lower(), char_id, 5))
    
    # Sort by priority (highest first) so we match full names before partial
    char_map.sort(key=lambda x: x[2], reverse=True)
    
    lines = []
    label = f"chapter_{chapter_num}_{gen.sanitize_name(chapter_title)}"
    
    lines.append(f"label {label}:")
    lines.append(f"    # {chapter_title}")
    lines.append("")
    lines.append("    scene bg default with fade")
    lines.append("")
    
    # Add brief scene description
    if scene_desc:
        lines.append("    # Scene")
        lines.append(f'    "{scene_desc[:200]}..."')
        lines.append("")
    
    # Split content into paragraphs
    # First try double newlines, but if that gives us giant blocks, split by sentences
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    
    # If we have very few or very long paragraphs, split by sentences instead
    if len(paragraphs) < 5 or any(len(p) > 1000 for p in paragraphs):
        # Split by sentence-ish boundaries
        import re
        sentences = re.split(r'(?<=[.!?])\s+', content)
        # Group into chunks of 3-5 sentences for better readability
        paragraphs = []
        for i in range(0, len(sentences), 4):
            chunk = " ".join(sentences[i:i+4])
            if chunk.strip() and len(chunk) > 50:
                paragraphs.append(chunk.strip())
    
    shown_chars = set()
    current_char = None
    
    # Show Old Bugs at the start since it's his story
    lines.append("    show old_bugs neutral at right with dissolve")
    shown_chars.add("old_bugs")
    current_char = "old_bugs"
    lines.append("")
    
    for i, para in enumerate(paragraphs[:150]):  # Limit to 150 paragraphs
        # Skip headers
        if para.startswith("Chapter ") or para.startswith("====") or len(para) < 20:
            continue
        
        # Check if any character is mentioned in this paragraph
        para_lower = para.lower()
        char_mentioned = None
        for search_term, char_id, priority in char_map:
            if search_term in para_lower:
                char_mentioned = char_id
                break  # Take first match (highest priority)
        
        # Check if this is dialogue (contains quotes)
        has_dialogue = '"' in para
        
        # Show character if mentioned and not currently showing
        if char_mentioned and char_mentioned != current_char and char_mentioned != "old_bugs":
            if char_mentioned not in shown_chars:
                lines.append(f"    show {char_mentioned} neutral at right with dissolve")
                shown_chars.add(char_mentioned)
                current_char = char_mentioned
            elif current_char:
                # Switch between characters - hide old, show new
                lines.append(f"    hide {current_char} with dissolve")
                lines.append(f"    show {char_mentioned} neutral at right with dissolve")
                current_char = char_mentioned
        
        # Check for simple dialogue patterns
        if has_dialogue:
            # Try to extract speaker and dialogue
            match = re.search(r'"([^"]+)",?\s+(?:said|cried|exclaimed|responded|announced|shouted)\s+(\w+)', para)
            if match:
                dialogue = match.group(1)
                speaker_name = match.group(2).lower()
                
                # Find matching character
                speaker_id = None
                for search_term, char_id, priority in char_map:
                    if speaker_name in search_term or search_term in speaker_name:
                        speaker_id = char_id
                        break
                
                if speaker_id and speaker_id != current_char:
                    if speaker_id not in shown_chars:
                        lines.append(f"    show {speaker_id} neutral at center with dissolve")
                        shown_chars.add(speaker_id)
                    current_char = speaker_id
                
                if speaker_id:
                    # Add dialogue
                    dialogue_lines = gen.wrap_dialogue(dialogue, 60)
                    if dialogue_lines:
                        lines.append(f'    {speaker_id} "{dialogue_lines[0]}"')
                        for dl in dialogue_lines[1:]:
                            lines.append(f'    extend " {dl}"')
                    lines.append("")
                    continue
        
        # Regular narration - don't wrap, show the full paragraph
        lines.append(f'    "{para}"')
        lines.append("")
    
    lines.append("    scene black with fade")
    lines.append('    "End of chapter"')
    lines.append("    return")
    lines.append("")
    
    # Write output
    with open(output_file, 'w') as f:
        f.write("\n".join(lines))
    
    print(f"Generated illustrated chapter: {output_file}")
    print(f"Characters shown: {shown_chars}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python simple_chapter_gen.py <analysis.json> <content.txt> <output.rpy>")
        sys.exit(1)
    
    create_simple_illustrated_chapter(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        Path(sys.argv[3])
    )

