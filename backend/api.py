from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import shutil
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
        
        # Load scenes to get count
        try:
            with open(scenes_file, 'r') as f:
                scenes = json.load(f)
                scenes_count = len(scenes)
        except:
            scenes_count = 0
        
        # Load character prompts to get character count
        character_prompts_file = book_dir / "character_prompts.json"
        characters_count = 0
        if character_prompts_file.exists():
            try:
                with open(character_prompts_file, 'r') as f:
                    char_data = json.load(f)
                    characters_count = len(char_data.get('characters', []))
            except:
                pass
        
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
            'scenes_count': scenes_count,
            'characters_count': characters_count
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
            
            # Get preview image from first scene
            scenes_file = chapter_dir / "scenes.json"
            if scenes_file.exists():
                try:
                    with open(scenes_file, 'r') as f:
                        scenes = json.load(f)
                        if scenes and len(scenes) > 0:
                            # Use the first scene's image as preview
                            first_scene_image = scenes[0].get('image_file', '')
                            if first_scene_image:
                                # Return full URL with correct host and port
                                chapter_info['preview_image'] = f"http://{FLASK_HOST}:{FLASK_PORT}/api/books/{book_id}/images/{first_scene_image}"
                except:
                    pass
            
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
    """Serve images from output/{book_id}/consistent_scenes/"""
    try:
        # Try consistent_scenes first
        image_file = OUTPUT_DIR / book_id / "consistent_scenes" / image_path
        
        # Fallback to scenes folder
        if not image_file.exists():
            image_file = OUTPUT_DIR / book_id / "scenes" / image_path
        
        # Fallback to images folder
        if not image_file.exists():
            image_file = OUTPUT_DIR / book_id / "images" / image_path
        
        if not image_file.exists():
            return jsonify({'error': f'Image not found: {image_path}'}), 404
        
        return send_file(image_file, mimetype='image/png')
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
