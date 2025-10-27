"""
Asset pipeline for organizing and processing book images for Ren'Py
"""
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image


class AssetPipeline:
    """Manages conversion of book generation assets to Ren'Py format"""
    
    # Standard Ren'Py sprite dimensions (reduced for better proportions)
    SPRITE_SIZE = (300, 600)  # width, height for character sprites
    BACKGROUND_SIZE = (1920, 1080)  # Full HD background
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        
    def sanitize_name(self, name: str) -> str:
        """Convert name to valid filesystem name"""
        sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        return sanitized.strip("_").lower()
    
    def process_character_image(self, 
                                image_path: Path,
                                output_path: Path,
                                resize: bool = True) -> Path:
        """Process a character image for use as a Ren'Py sprite"""
        try:
            img = Image.open(image_path)
            
            # Convert to RGBA if not already
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Resize to standard sprite size if requested
            if resize:
                # Maintain aspect ratio
                img.thumbnail(self.SPRITE_SIZE, Image.Resampling.LANCZOS)
            
            # Save as PNG
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', optimize=True)
            
            return output_path
            
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            # Copy original if processing fails
            shutil.copy2(image_path, output_path)
            return output_path
    
    def organize_character_sprites(self,
                                   images_dir: Path,
                                   game_dir: Path,
                                   characters: List[Dict[str, str]]) -> Dict[str, List[Path]]:
        """
        Organize character images into Ren'Py images directory
        
        Returns mapping of character_id -> list of sprite files
        """
        images_output = game_dir / "images" / "characters"
        images_output.mkdir(parents=True, exist_ok=True)
        
        character_sprites = {}
        
        for char in characters:
            char_name = char.get("name", "Unknown")
            char_id = self.sanitize_name(char_name)
            
            # Try multiple filename variations
            name_variations = [
                char_name,  # Original name with spaces
                char_name.replace(" ", "_"),  # Underscores
                char_name.replace(" ", ""),  # No spaces
            ]
            
            # Look for base character image
            base_image = None
            for name_var in name_variations:
                test_path = images_dir / f"{name_var}.png"
                if test_path.exists():
                    base_image = test_path
                    break
            
            if base_image:
                output_path = images_output / f"{char_id}.png"
                self.process_character_image(base_image, output_path)
                character_sprites[char_id] = [output_path]
            
            # Look for expression images
            expressions_dir = None
            for name_var in name_variations:
                test_dir = images_dir / f"{name_var}_expressions"
                if test_dir.exists():
                    expressions_dir = test_dir
                    break
            
            if expressions_dir:
                if char_id not in character_sprites:
                    character_sprites[char_id] = []
                
                for expr_file in expressions_dir.glob("*.png"):
                    # Extract expression name from filename
                    # Format: CharName_expression.png or CharName_talking_expression.png
                    expr_name = expr_file.stem
                    
                    # Remove character name prefix (try all variations)
                    for name_var in name_variations:
                        name_prefix = name_var.replace(" ", "_")
                        if expr_name.startswith(name_prefix):
                            expr_name = expr_name[len(name_prefix):].lstrip("_")
                            break
                    
                    output_name = f"{char_id}_{expr_name}.png"
                    output_path = images_output / output_name
                    self.process_character_image(expr_file, output_path)
                    character_sprites[char_id].append(output_path)
        
        return character_sprites
    
    def create_background_from_scene(self,
                                     scene_description: str,
                                     output_path: Path) -> Path:
        """
        Create a background image placeholder
        In production, this would generate an image from the scene description
        """
        # For now, create a simple colored background based on mood
        img = Image.new('RGB', self.BACKGROUND_SIZE, color='#1a1a1a')
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, 'PNG')
        
        return output_path
    
    def organize_environment_images(self,
                                    environments_dir: Path,
                                    game_dir: Path) -> Dict[str, Path]:
        """
        Organize environment/background images into Ren'Py images directory
        
        Args:
            environments_dir: Source directory with environment images
            game_dir: Ren'Py game directory
            
        Returns:
            Dictionary mapping bg names to file paths
        """
        if not environments_dir.exists():
            return {}
        
        images_output = game_dir / "images" / "backgrounds"
        images_output.mkdir(parents=True, exist_ok=True)
        
        environment_images = {}
        
        # Copy all PNG files from environments directory
        for env_file in environments_dir.glob("*.png"):
            bg_name = env_file.stem  # e.g., "old_bugs" from "old_bugs.png"
            output_path = images_output / env_file.name
            
            try:
                # Resize to standard background size if needed
                img = Image.open(env_file)
                
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large or too small
                if img.size != self.BACKGROUND_SIZE:
                    img = img.resize(self.BACKGROUND_SIZE, Image.Resampling.LANCZOS)
                
                img.save(output_path, 'PNG', optimize=True)
                environment_images[bg_name] = output_path
                print(f"  Processed background: {bg_name}")
                
            except Exception as e:
                print(f"Error processing {env_file}: {e}")
                # Copy original if processing fails
                shutil.copy2(env_file, output_path)
                environment_images[bg_name] = output_path
        
        return environment_images
    
    def generate_image_definitions(self,
                                   character_sprites: Dict[str, List[Path]],
                                   game_dir: Path,
                                   environment_images: Dict[str, Path] = None) -> Path:
        """Generate Ren'Py image definitions for all sprites and backgrounds"""
        lines = [
            "# Image definitions",
            "# Auto-generated character sprites and expressions",
            "",
        ]
        
        for char_id, sprite_files in character_sprites.items():
            lines.append(f"# {char_id} sprites")
            
            for sprite_path in sprite_files:
                # Extract expression/variant from filename
                filename = sprite_path.stem
                
                # Parse filename: char_id or char_id_expression
                # Remove char_id prefix to get just the expression
                if filename.startswith(char_id + "_"):
                    expression = filename[len(char_id) + 1:]
                elif filename == char_id:
                    # Base sprite
                    expression = "neutral"
                else:
                    # Fallback
                    expression = filename.replace(char_id, "").lstrip("_") or "neutral"
                
                # Relative path from game/images
                rel_path = sprite_path.relative_to(game_dir)
                
                # Generate image definition
                lines.append(f'image {char_id} {expression} = "{rel_path}"')
            
            lines.append("")
        
        # Add background definitions
        lines.append("# Backgrounds")
        
        if environment_images:
            for bg_name, bg_path in environment_images.items():
                rel_path = bg_path.relative_to(game_dir)
                lines.append(f'image bg {bg_name} = "{rel_path}"')
            lines.append("")
        
        # Add default backgrounds
        lines.append('image bg default = "#1a1a1a"')
        lines.append('image black = "#000000"')
        lines.append("")
        
        # Write to images.rpy
        images_file = game_dir / "images.rpy"
        with open(images_file, "w") as f:
            f.write("\n".join(lines))
        
        return images_file
    
    def setup_renpy_structure(self, game_dir: Path):
        """Create the basic Ren'Py project structure"""
        game_path = game_dir / "game"
        game_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (game_path / "images").mkdir(exist_ok=True)
        (game_path / "audio").mkdir(exist_ok=True)
        (game_path / "gui").mkdir(exist_ok=True)
        
        # Create options.rpy with basic configuration
        options_content = '''## Options.rpy - Game configuration

define config.name = "Book Visual Novel"
define config.version = "1.0"

define config.window_icon = None
define config.screen_width = 1280
define config.screen_height = 720

define config.save_directory = "book-vn-saves"

init python:
    build.classify('**~', None)
    build.classify('**.bak', None)
    build.classify('**/.**', None)
    build.classify('**/#**', None)
    build.classify('**/thumbs.db', None)
    
define config.has_sound = True
define config.has_music = True
define config.has_voice = False

define config.main_menu_music = None
define config.enter_transition = dissolve
define config.exit_transition = dissolve
define config.intra_transition = dissolve
define config.after_load_transition = None
define config.end_game_transition = None

define config.window = "auto"
define config.window_show_transition = Dissolve(.2)
define config.window_hide_transition = Dissolve(.2)

default preferences.text_cps = 35
default preferences.afm_time = 15
'''
        
        options_file = game_path / "options.rpy"
        with open(options_file, "w") as f:
            f.write(options_content)
        
        return game_path
    
    def process_book_assets(self,
                          book_output_dir: Path,
                          renpy_project_dir: Path) -> Dict[str, any]:
        """
        Process all assets from a book generation output directory
        
        Args:
            book_output_dir: Path to output/BookName directory
            renpy_project_dir: Path to Ren'Py project directory
        
        Returns:
            Dictionary with asset processing results
        """
        results = {
            "character_sprites": {},
            "backgrounds": {},
            "image_definitions": None,
            "game_dir": None
        }
        
        # Set up Ren'Py structure
        game_dir = self.setup_renpy_structure(renpy_project_dir)
        results["game_dir"] = game_dir
        
        # Load analysis to get character list
        analysis_file = book_output_dir / "analysis.json"
        if not analysis_file.exists():
            print(f"Warning: No analysis.json found in {book_output_dir}")
            return results
        
        with open(analysis_file) as f:
            analysis = json.load(f)
            if isinstance(analysis, list):
                analysis = analysis[0]
        
        characters = analysis.get("characters", [])
        character_sprites = {}
        
        # Process character sprites
        images_dir = book_output_dir / "images"
        if images_dir.exists():
            character_sprites = self.organize_character_sprites(
                images_dir,
                game_dir,
                characters
            )
            results["character_sprites"] = character_sprites
        
        # Process environment/background images
        environments_dir = book_output_dir / "environments"
        environment_images = {}
        if environments_dir.exists():
            print("Processing environment images...")
            environment_images = self.organize_environment_images(
                environments_dir,
                game_dir
            )
            results["backgrounds"] = environment_images
            print(f"  ✓ Processed {len(environment_images)} environment(s)")
        
        # Create default background if no environments exist
        if not environment_images:
            bg_output = game_dir / "images" / "backgrounds" / "default.png"
            scene_desc = analysis.get("scene_description", "")
            self.create_background_from_scene(scene_desc, bg_output)
            environment_images["default"] = bg_output
            results["backgrounds"]["default"] = bg_output
        
        # Generate image definitions with both characters and backgrounds
        images_def = self.generate_image_definitions(
            character_sprites, 
            game_dir,
            environment_images
        )
        results["image_definitions"] = images_def
        
        return results


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python asset_pipeline.py <book_output_dir> <renpy_project_dir>")
        sys.exit(1)
    
    book_output_dir = Path(sys.argv[1])
    renpy_project_dir = Path(sys.argv[2])
    
    pipeline = AssetPipeline(renpy_project_dir)
    results = pipeline.process_book_assets(book_output_dir, renpy_project_dir)
    
    print("\nAsset processing complete!")
    print(f"Game directory: {results['game_dir']}")
    print(f"Character sprites: {len(results['character_sprites'])} characters")
    for char_id, sprites in results['character_sprites'].items():
        print(f"  {char_id}: {len(sprites)} sprites")
    print(f"Backgrounds: {len(results['backgrounds'])} files")
    print(f"Image definitions: {results['image_definitions']}")


if __name__ == "__main__":
    main()

