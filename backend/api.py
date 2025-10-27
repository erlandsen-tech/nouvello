from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import shutil
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Base paths
BOOKS_JSON_PATH = Path(__file__).parent.parent / "frontend" / "public" / "data" / "books.json"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
FRONTEND_DATA_DIR = Path(__file__).parent.parent / "frontend" / "public" / "data"

@app.route('/api/books', methods=['GET'])
def get_books():
    """Get all books from books.json"""
    try:
        with open(BOOKS_JSON_PATH, 'r') as f:
            books = json.load(f)
        return jsonify(books)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/<book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book and all its associated data"""
    try:
        # Load current books
        with open(BOOKS_JSON_PATH, 'r') as f:
            books = json.load(f)
        
        # Find the book to delete
        book_to_delete = None
        for book in books:
            if book['id'] == book_id:
                book_to_delete = book
                break
        
        if not book_to_delete:
            return jsonify({'error': 'Book not found'}), 404
        
        # Delete the book from the list
        books = [book for book in books if book['id'] != book_id]
        
        # Update books.json
        with open(BOOKS_JSON_PATH, 'w') as f:
            json.dump(books, f, indent=2)
        
        # Delete book data directories
        data_dir = book_to_delete.get('data_dir', book_id)
        
        # Delete from output directory
        output_book_dir = OUTPUT_DIR / data_dir
        if output_book_dir.exists():
            shutil.rmtree(output_book_dir)
        
        # Delete from frontend data directory
        frontend_book_dir = FRONTEND_DATA_DIR / data_dir
        if frontend_book_dir.exists():
            shutil.rmtree(frontend_book_dir)
        
        # Delete associated images
        images_dir = Path(__file__).parent.parent / "frontend" / "public" / "images"
        for image_type in ['characters', 'environments', 'scenes']:
            image_dir = images_dir / image_type
            if image_dir.exists():
                # Delete images that match the book pattern
                for image_file in image_dir.glob(f"*{book_id}*"):
                    image_file.unlink()
        
        return jsonify({'message': f'Book {book_id} deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
