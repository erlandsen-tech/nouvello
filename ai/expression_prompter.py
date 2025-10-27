"""
Expression Prompt Generator
Generates image-to-image editing prompts for character expressions
Creates variations of base character images with different moods/expressions
"""

import json
import os
from typing import List, Dict
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# Common VN expressions
COMMON_EXPRESSIONS = {
    "neutral": {
        "name": "Neutral",
        "description": "Default calm expression, relaxed face, neutral mouth, looking straight ahead"
    },
    "happy": {
        "name": "Happy",
        "description": "Warm smile, bright eyes, slightly raised cheeks, friendly and welcoming expression"
    },
    "sad": {
        "name": "Sad",
        "description": "Downcast eyes, slightly frowning mouth, melancholic expression, subdued demeanor"
    },
    "angry": {
        "name": "Angry",
        "description": "Furrowed brow, intense glare, tense jaw, stern or hostile expression"
    },
    "surprised": {
        "name": "Surprised",
        "description": "Wide eyes, raised eyebrows, slightly open mouth, startled expression"
    },
    "worried": {
        "name": "Worried",
        "description": "Concerned look, slightly furrowed brow, tense expression, anxious eyes"
    },
    "embarrassed": {
        "name": "Embarrassed",
        "description": "Blushing cheeks, shy expression, looking slightly away, bashful demeanor"
    },
    "thinking": {
        "name": "Thinking",
        "description": "Contemplative expression, slightly narrowed eyes, hand near chin or thoughtful pose"
    },
    "talking": {
        "name": "Talking",
        "description": "Mouth slightly open in mid-speech, animated expression, engaged demeanor"
    },
    "talking_happy": {
        "name": "Talking (Happy)",
        "description": "Speaking with a smile, mouth open cheerfully, animated happy expression"
    },
    "talking_angry": {
        "name": "Talking (Angry)",
        "description": "Speaking with anger, mouth open in stern expression, intense hostile demeanor"
    },
    "smirking": {
        "name": "Smirking",
        "description": "Slight smirk or knowing smile, one corner of mouth raised, clever expression"
    },
    "scared": {
        "name": "Scared",
        "description": "Wide fearful eyes, tense expression, mouth slightly open in fear"
    },
    "determined": {
        "name": "Determined",
        "description": "Focused intense gaze, firm mouth, resolute expression showing determination"
    }
}


@dataclass
class ExpressionPrompt:
    """Expression variation prompt for a character"""
    character_name: str
    expression: str
    expression_name: str
    editing_prompt: str
    consistency_notes: str
    
    def to_dict(self) -> dict:
        return asdict(self)


class ExpressionPrompter:
    """Generate expression variation prompts for characters"""
    
    def __init__(self, expressions: Dict = None):
        """
        Initialize with expression definitions
        
        Args:
            expressions: Dict of expression definitions (uses COMMON_EXPRESSIONS if None)
        """
        self.expressions = expressions or COMMON_EXPRESSIONS
    
    def generate_expression_prompts(self, character_name: str, 
                                   base_prompt: str,
                                   book_context: str = "") -> List[ExpressionPrompt]:
        """
        Generate expression variation prompts for a character
        
        Args:
            character_name: Name of the character
            base_prompt: The base character description/prompt
            book_context: Context about the book's style/mood
            
        Returns:
            List of ExpressionPrompt objects
        """
        prompts = []
        
        # Extract key visual elements from base prompt (appearance, clothing, style)
        consistency_base = self._extract_consistency_elements(base_prompt)
        
        for expr_key, expr_data in self.expressions.items():
            editing_prompt = self._build_editing_prompt(
                character_name,
                base_prompt,
                expr_data,
                consistency_base,
                book_context
            )
            
            prompt = ExpressionPrompt(
                character_name=character_name,
                expression=expr_key,
                expression_name=expr_data["name"],
                editing_prompt=editing_prompt,
                consistency_notes=consistency_base
            )
            prompts.append(prompt)
        
        return prompts
    
    def _extract_consistency_elements(self, base_prompt: str) -> str:
        """Extract key visual elements to maintain consistency"""
        # This is a simplified version - could be enhanced with LLM
        return (
            "CONSISTENCY REQUIREMENTS:\n"
            "- Maintain identical character design, proportions, and art style\n"
            "- Keep the same clothing, hairstyle, hair color, and accessories\n"
            "- Preserve the same lighting, color palette, and artistic rendering\n"
            "- Only modify the facial expression and associated body language\n"
            "- Ensure the character remains instantly recognizable"
        )
    
    def _build_editing_prompt(self, character_name: str, base_prompt: str,
                             expression_data: Dict, consistency_base: str,
                             book_context: str) -> str:
        """Build the editing prompt for an expression"""
        
        # Extract first 200 chars of base prompt for context
        base_context = base_prompt[:200] + "..." if len(base_prompt) > 200 else base_prompt
        
        prompt = f"""Edit this character image to show a {expression_data['name'].lower()} expression.

CHARACTER: {character_name}
BASE DESCRIPTION: {base_context}

NEW EXPRESSION: {expression_data['description']}

{consistency_base}

EDITING INSTRUCTIONS:
Create a variation of the same character with a {expression_data['name'].lower()} expression. The character's core appearance, clothing, pose, and artistic style must remain identical - only change the facial expression and subtle body language that naturally accompanies this emotion. Ensure the character is immediately recognizable as the same person.

Style note: {book_context if book_context else 'Maintain the original artistic style'}"""

        return prompt
    
    def generate_from_character_prompts_file(self, prompts_file: str,
                                            output_dir: str) -> Dict[str, List[ExpressionPrompt]]:
        """
        Generate expression prompts for all characters from a prompts file
        
        Args:
            prompts_file: Path to character_prompts.json
            output_dir: Directory to save expression prompts
            
        Returns:
            Dict mapping character names to their expression prompts
        """
        print(f"📖 Loading character prompts from: {prompts_file}")
        
        with open(prompts_file, 'r', encoding='utf-8') as f:
            characters = json.load(f)
        
        print(f"✅ Loaded {len(characters)} characters")
        
        all_expressions = {}
        
        print(f"🎭 Generating expressions for {len(characters)} characters in parallel...")
        
        def generate_single_character_expressions(char):
            """Generate expressions for a single character - used for parallel execution"""
            char_name = char.get("character_name", "Unknown")
            base_prompt = char.get("image_prompt", "")
            book_context = char.get("book_context", "")
            
            try:
                expression_prompts = self.generate_expression_prompts(
                    char_name,
                    base_prompt,
                    book_context
                )
                
                # Export individual character expression file
                char_output_dir = os.path.join(output_dir, self._sanitize_filename(char_name))
                os.makedirs(char_output_dir, exist_ok=True)
                
                output_file = os.path.join(char_output_dir, "expressions.json")
                self._export_expressions(expression_prompts, output_file)
                
                print(f"   ✅ {char_name}: {len(expression_prompts)} expressions saved")
                return char_name, expression_prompts
                
            except Exception as e:
                print(f"   ⚠️  Error with {char_name}: {e}")
                return char_name, []
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            future_to_char = {
                executor.submit(generate_single_character_expressions, char): char.get("character_name", "Unknown")
                for char in characters
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_char):
                char_name = future_to_char[future]
                try:
                    char_name_result, expression_prompts = future.result()
                    all_expressions[char_name_result] = expression_prompts
                except Exception as e:
                    print(f"   ❌ Unexpected error with {char_name}: {e}")
                    all_expressions[char_name] = []
        
        # Also create a master index
        master_file = os.path.join(output_dir, "all_expressions.json")
        self._export_master_index(all_expressions, master_file)
        print(f"\n📋 Master index saved: {master_file}")
        
        return all_expressions
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize character name for filename"""
        import re
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = re.sub(r'\s+', '_', name)
        return name.strip('_')
    
    def _export_expressions(self, prompts: List[ExpressionPrompt], output_file: str):
        """Export expression prompts to JSON"""
        data = [p.to_dict() for p in prompts]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _export_master_index(self, all_expressions: Dict, output_file: str):
        """Export master index of all characters and expressions"""
        data = {}
        for char_name, prompts in all_expressions.items():
            data[char_name] = [p.to_dict() for p in prompts]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    """Command-line interface"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate expression variation prompts for characters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate expression prompts from character prompts file
  %(prog)s book_character_prompts.json -o prompts/

  # This will create:
  #   prompts/Character_Name/expressions.json
  #   prompts/all_expressions.json
        """
    )
    
    parser.add_argument(
        'prompts_file',
        help='Path to character_prompts.json file'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='prompts',
        help='Output directory for expression prompts (default: prompts)'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.prompts_file):
        print(f"❌ Error: File not found: {args.prompts_file}")
        sys.exit(1)
    
    # Initialize prompter
    print("🚀 Initializing Expression Prompter")
    print(f"   Expressions: {len(COMMON_EXPRESSIONS)} variations")
    
    prompter = ExpressionPrompter()
    
    # Generate expression prompts
    print("\n🎭 Generating expression prompts...")
    print("=" * 70)
    
    all_expressions = prompter.generate_from_character_prompts_file(
        args.prompts_file,
        args.output_dir
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ GENERATION COMPLETE!")
    print("=" * 70)
    print(f"Characters processed: {len(all_expressions)}")
    print(f"Expressions per character: {len(COMMON_EXPRESSIONS)}")
    print(f"Total prompts: {len(all_expressions) * len(COMMON_EXPRESSIONS)}")
    print(f"\nOutput directory: {args.output_dir}/")
    print(f"\nStructure:")
    print(f"  📁 {args.output_dir}/")
    print(f"     ├── all_expressions.json")
    print(f"     ├── Character_1/")
    print(f"     │   └── expressions.json")
    print(f"     ├── Character_2/")
    print(f"     │   └── expressions.json")
    print(f"     └── ...")


if __name__ == "__main__":
    main()

