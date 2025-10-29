import React, { useState, useEffect } from 'react';
import './BookChooser.css';

// Get API URL from environment variable
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

interface Book {
  id: string;
  title: string;
  description: string;
  data_dir: string;
  created_at: string;
  scenes_count: number;
  characters_count: number;
  cover_image?: string;
}

interface BookChooserProps {
  onBookSelect: (bookId: string) => void;
}

const BookChooser: React.FC<BookChooserProps> = ({ onBookSelect }) => {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBooks();
  }, []);

  const loadBooks = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/books`);
      if (!response.ok) {
        throw new Error('Failed to load books');
      }
      const booksData: Book[] = await response.json();
      
      // For each book, load the first scene image as cover
      const booksWithCovers = await Promise.all(
        booksData.map(async (book) => {
          try {
            const scenesResponse = await fetch(`${API_BASE_URL}/books/${book.data_dir}/scenes`);
            if (scenesResponse.ok) {
              const scenes = await scenesResponse.json();
              if (scenes.length > 0 && scenes[0].image_file) {
                // Use backend API URL for image
                const imageFile = scenes[0].image_file.startsWith('http') 
                  ? scenes[0].image_file 
                  : `${API_BASE_URL}/books/${book.data_dir}/images/${scenes[0].image_file}`;
                return { ...book, cover_image: imageFile };
              }
            }
          } catch (err) {
            console.warn(`Could not load cover for ${book.id}`);
          }
          return book;
        })
      );
      
      setBooks(booksWithCovers);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load books');
    } finally {
      setLoading(false);
    }
  };

  const handleBookSelect = (bookId: string) => {
    onBookSelect(bookId);
  };

  const handleDeleteBook = async (bookId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent triggering the book selection
    
    if (!window.confirm('Are you sure you want to delete this book? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/books/${bookId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete book');
      }

      // Reload books after successful deletion
      await loadBooks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete book');
    }
  };

  if (loading) {
    return (
      <div className="book-chooser">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading books...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="book-chooser">
        <div className="error-container">
          <h2>Error Loading Books</h2>
          <p>{error}</p>
          <button onClick={loadBooks}>Try Again</button>
        </div>
      </div>
    );
  }

  if (books.length === 0) {
    return (
      <div className="book-chooser">
        <div className="no-books-container">
          <h2>No Books Available</h2>
          <p>No visual novels have been generated yet.</p>
          <div className="instructions">
            <h3>How to add books:</h3>
            <ol>
              <li>Place EPUB files in the <code>books/</code> directory</li>
              <li>Run: <code>python book_to_vn.py books/your_book.epub</code></li>
              <li>Refresh this page</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="book-chooser">
      <div className="book-chooser-header">
        <h1>📚 Visual Novel Library</h1>
        <p>Choose a book to read</p>
      </div>
      
      <div className="books-grid">
        {books.map((book) => (
          <div 
            key={book.id} 
            className="book-card"
            onClick={() => handleBookSelect(book.id)}
          >
            <div className="book-cover">
              {book.cover_image ? (
                <img src={book.cover_image} alt={`${book.title} cover`} className="book-cover-image" />
              ) : (
                <div className="book-icon">📖</div>
              )}
            </div>
            <div className="book-info">
              <h3>{book.title}</h3>
              <p className="book-description">{book.description}</p>
              <div className="book-stats">
                <span className="stat">
                  <strong>{book.scenes_count}</strong> scenes
                </span>
                <span className="stat">
                  <strong>{book.characters_count}</strong> characters
                </span>
              </div>
            </div>
            <div className="book-action">
              <button className="read-button">Read Now</button>
              <button 
                className="delete-button"
                onClick={(e) => handleDeleteBook(book.id, e)}
                title="Delete book"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>
      
      <div className="book-chooser-footer">
        Copyright AIAKAKI 2025
      </div>
    </div>
  );
};

export default BookChooser;
