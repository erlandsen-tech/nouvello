from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import json
import shutil
import random
from pathlib import Path
from config import OUTPUT_DIR, CORS_ORIGINS, FLASK_PORT, FLASK_HOST, DEBUG

app = Flask(__name__)

# Enable CORS for all routes with configuration from config.py
CORS(app, resources={
    r"/api/*": {
        "origins": CORS_ORIGINS,
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

def scan_output_books():
    """Scan the output directory and return list of all books"""
    books = []
    
    if not OUTPUT_DIR.exists():
        return books
    
    for book_dir in OUTPUT_DIR.iterdir():
        if not book_dir.is_dir():
            continue
            
        book_id = book_dir.name
        scenes_file = book_dir / "scenes.json"
        
        # Skip if no scenes.json exists
        if not scenes_file.exists():
            continue
        
        # Load scenes to get count (for backward compatibility)
        try:
            with open(scenes_file, 'r') as f:
                scenes = json.load(f)
                scenes_count = len(scenes)
        except:
            scenes_count = 0
        
        # Load character prompts to get character count (for backward compatibility)
        character_prompts_file = book_dir / "character_prompts.json"
        characters_count = 0
        if character_prompts_file.exists():
            try:
                with open(character_prompts_file, 'r') as f:
                    char_data = json.load(f)
                    characters_count = len(char_data.get('characters', []))
            except:
                pass
        
        # Count chapters
        chapters_dir = book_dir / "chapters"
        chapters_count = 0
        if chapters_dir.exists():
            chapters_count = len([d for d in chapters_dir.iterdir() if d.is_dir()])
        
        # Get book title - use book_id formatted nicely as default
        title = book_id.replace('_', ' ').title()
        description = f"Visual novel adaptation of {title}"
        author = None
        
        # Try to get book title from analysis metadata
        analysis_file = book_dir / "analysis.json"
        if analysis_file.exists():
            try:
                with open(analysis_file, 'r') as f:
                    analysis = json.load(f)
                    
                    # New format: {book_title, book_author, chapters: [...]}
                    if isinstance(analysis, dict) and 'book_title' in analysis:
                        if analysis.get('book_title'):
                            title = analysis['book_title']
                        if analysis.get('book_author'):
                            author = analysis['book_author']
                            description = f"Visual novel adaptation of {title} by {author}"
                    # Old format: [...chapters...]
                    elif isinstance(analysis, list) and len(analysis) > 0:
                        first_chapter_title = analysis[0].get('chapter_title', '')
                        # If chapter title contains "CHAPTER", the book name is probably the folder name
                        if 'CHAPTER' not in first_chapter_title.upper():
                            title = first_chapter_title
            except:
                pass
        
        books.append({
            'id': book_id,
            'title': title,
            'description': description,
            'data_dir': book_id,
            'created_at': '',
            'scenes_count': scenes_count,  # Kept for backward compatibility
            'characters_count': characters_count,  # Kept for backward compatibility
            'chapters_count': chapters_count
        })
    
    return books

@app.route('/api/books', methods=['GET'])
def get_books():
    """Get all books by scanning output directory"""
    try:
        books = scan_output_books()
        return jsonify(books)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/chapters', methods=['GET'])
def get_book_chapters(book_id):
    """Get list of available chapters for a book"""
    try:
        chapters_dir = OUTPUT_DIR / book_id / "chapters"
        
        if not chapters_dir.exists():
            return jsonify({'chapters': []})
        
        # Scan for chapter directories
        chapters = []
        for chapter_dir in sorted(chapters_dir.iterdir()):
            if not chapter_dir.is_dir():
                continue
            
            # Load chapter analysis if available
            analysis_file = chapter_dir / "analysis.json"
            chapter_info = {
                'id': chapter_dir.name,
                'title': chapter_dir.name.replace('_', ' '),
                'number': None,
                'preview_image': None
            }
            
            if analysis_file.exists():
                try:
                    with open(analysis_file, 'r') as f:
                        analysis = json.load(f)
                        if isinstance(analysis, dict):
                            chapter_info['title'] = analysis.get('chapter_title', chapter_info['title'])
                            chapter_info['number'] = analysis.get('chapter_number')
                except:
                    pass
            
            # Get preview image and scene count from first scene
            scenes_file = chapter_dir / "scenes.json"
            scene_count = 0
            if scenes_file.exists():
                try:
                    with open(scenes_file, 'r') as f:
                        scenes = json.load(f)
                        scene_count = len(scenes) if scenes else 0
                        if scenes and len(scenes) > 0:
                            # Use the first scene's image as preview
                            first_scene_image = scenes[0].get('image_file', '')
                            if first_scene_image:
                                # Return full URL with correct host and port
                                chapter_info['preview_image'] = f"http://{FLASK_HOST}:{FLASK_PORT}/api/books/{book_id}/images/{first_scene_image}"
                except:
                    pass
            
            chapter_info['scenes_count'] = scene_count
            chapters.append(chapter_info)
        
        return jsonify({'chapters': chapters})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/chapters/<chapter_id>', methods=['GET'])
def get_book_chapter_scenes(book_id, chapter_id):
    """Get scenes for a specific chapter"""
    try:
        chapter_dir = OUTPUT_DIR / book_id / "chapters" / chapter_id
        scenes_file = chapter_dir / "scenes.json"
        
        if scenes_file.exists():
            with open(scenes_file, 'r') as f:
                scenes = json.load(f)
            return jsonify(scenes)
        
        # Fallback to book-level scenes if no chapter-specific scenes
        scenes_file = OUTPUT_DIR / book_id / "scenes.json"
        if scenes_file.exists():
            with open(scenes_file, 'r') as f:
                scenes = json.load(f)
            return jsonify(scenes)
        
        return jsonify({'error': f'No scenes found for chapter {chapter_id}'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/scenes', methods=['GET'])
def get_book_scenes(book_id):
    """Get scenes.json for a specific book from output directory"""
    try:
        scenes_file = OUTPUT_DIR / book_id / "scenes.json"
        
        if not scenes_file.exists():
            return jsonify({'error': f'scenes.json not found for book {book_id}'}), 404
        
        with open(scenes_file, 'r') as f:
            scenes = json.load(f)
        
        return jsonify(scenes)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>/images/<path:image_path>', methods=['GET'])
def get_book_image(book_id, image_path):
    """Serve images from output/{book_id}/consistent_scenes/ or style-specific directories"""
    try:
        book_dir = OUTPUT_DIR / book_id
        
        # List of directories to check in order of priority
        image_paths_to_try = []
        
        # 1. Check for style-specific directories (consistent_scenes_{style})
        # Try to get style from analysis.json
        analysis_file = book_dir / "analysis.json"
        style_safe = None
        if analysis_file.exists():
            try:
                with open(analysis_file, 'r') as f:
                    analysis = json.load(f)
                    if isinstance(analysis, dict) and 'art_style' in analysis:
                        art_style = analysis.get('art_style')
                        if art_style:
                            # Create style-safe directory name (matching how it's created in book_to_vn.py)
                            style_safe = "".join(c for c in art_style if c.isalnum() or c in (' ', '-', '_')).strip()
                            style_safe = style_safe.replace(' ', '_').lower()
                            style_dir = book_dir / f"consistent_scenes_{style_safe}"
                            if style_dir.exists():
                                image_paths_to_try.append(style_dir / image_path)
            except Exception:
                pass
        
        # 2. Also check all style-specific directories (in case style changed or multiple exist)
        if book_dir.exists():
            for scene_dir in book_dir.glob("consistent_scenes_*"):
                if scene_dir.is_dir():
                    image_paths_to_try.append(scene_dir / image_path)
        
        # 3. Default consistent_scenes directory
        image_paths_to_try.append(book_dir / "consistent_scenes" / image_path)
        
        # 4. Fallback to scenes folder
        image_paths_to_try.append(book_dir / "scenes" / image_path)
        
        # 5. Fallback to images folder (for character images)
        image_paths_to_try.append(book_dir / "images" / image_path)
        
        # Try each path in order
        for image_file in image_paths_to_try:
            if image_file.exists() and image_file.is_file():
                # Read the image file and create response with explicit headers to avoid CORB issues
                with open(image_file, 'rb') as f:
                    image_data = f.read()
                
                response = Response(image_data, mimetype='image/png')
                # Set headers to prevent CORB issues
                # CORS will be handled by flask-cors automatically, but we ensure Content-Type is explicit
                response.headers['Content-Type'] = 'image/png'
                response.headers['X-Content-Type-Options'] = 'nosniff'
                return response
        
        # If not found, try to find a fallback image from scene directories
        # Prioritize style-specific directories, then default scene directories
        fallback_image = None
        
        # Determine if this is a scene image (starts with "scene_") or character image
        is_scene_image = image_path.startswith("scene_")
        
        if is_scene_image:
            # For scene images, look in scene directories only
            fallback_dirs = []
            
            # 1. Check style-specific scene directories first (prioritize the one from analysis.json)
            if book_dir.exists():
                analysis_file = book_dir / "analysis.json"
                if analysis_file.exists():
                    try:
                        with open(analysis_file, 'r') as f:
                            analysis = json.load(f)
                            if isinstance(analysis, dict) and 'art_style' in analysis:
                                art_style = analysis.get('art_style')
                                if art_style:
                                    style_safe = "".join(c for c in art_style if c.isalnum() or c in (' ', '-', '_')).strip()
                                    style_safe = style_safe.replace(' ', '_').lower()
                                    style_dir = book_dir / f"consistent_scenes_{style_safe}"
                                    if style_dir.exists():
                                        fallback_dirs.append(style_dir)
                    except Exception:
                        pass
                
                # Add all style-specific directories
                for style_dir in book_dir.glob("consistent_scenes_*"):
                    if style_dir.is_dir() and style_dir not in fallback_dirs:
                        fallback_dirs.append(style_dir)
            
            # 2. Check default scene directories
            fallback_dirs.append(book_dir / "consistent_scenes")
            fallback_dirs.append(book_dir / "scenes")
        else:
            # For character images, look in character images directory
            fallback_dirs = [book_dir / "images"]
        
        # Try to find a fallback image
        for fallback_dir in fallback_dirs:
            if fallback_dir.exists() and fallback_dir.is_dir():
                png_files = list(fallback_dir.glob("*.png"))
                if png_files:
                    fallback_image = random.choice(png_files)
                    break
        
        if fallback_image:
            # Return random fallback image
            with open(fallback_image, 'rb') as f:
                image_data = f.read()
            
            response = Response(image_data, mimetype='image/png')
            response.headers['Content-Type'] = 'image/png'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Fallback-Image'] = 'true'  # Indicate this is a fallback
            return response
        
        # If no fallback found, return 404
        return jsonify({'error': f'Image not found: {image_path}'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book and all its associated data from output directory"""
    try:
        output_book_dir = OUTPUT_DIR / book_id
        
        if not output_book_dir.exists():
            return jsonify({'error': 'Book not found'}), 404
        
        # Delete from output directory
        shutil.rmtree(output_book_dir)
        
        return jsonify({'message': f'Book {book_id} deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Flask Backend Starting...")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"📚 Books found: {len(scan_output_books())}")
    print(f"🌐 Server: http://localhost:{FLASK_PORT}")
    print(f"🔗 CORS enabled for: {', '.join(CORS_ORIGINS)}")
    print(f"🐛 Debug mode: {DEBUG}")
    print("=" * 60)
    app.run(debug=DEBUG, port=FLASK_PORT, host=FLASK_HOST)
