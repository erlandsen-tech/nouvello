import React, { useState, useEffect } from 'react';
import BookReader from './components/BookReader';
import BookChooser from './components/BookChooser';
import ChapterChooser from './components/ChapterChooser';
import { BookData } from './types';
import { loadBookData } from './utils/dataLoader';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

interface Book {
  id: string;
  title: string;
}

function App() {
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<string | null>(null);
  const [bookData, setBookData] = useState<BookData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBookSelect = async (bookId: string) => {
    // Fetch book title for chapter chooser
    try {
      const response = await fetch(`${API_BASE_URL}/books`);
      const books = await response.json();
      const book = books.find((b: any) => b.id === bookId);
      setSelectedBook({ id: bookId, title: book?.title || bookId });
    } catch (err) {
      setSelectedBook({ id: bookId, title: bookId });
    }
    setSelectedChapter(null);
    setBookData(null);
    setError(null);
  };

  const handleChapterSelect = async (chapterId: string) => {
    if (!selectedBook) return;
    
    setSelectedChapter(chapterId);
    setLoading(true);
    setError(null);
    
    try {
      let data;
      
      // If there's a specific chapter, load its scenes
      if (chapterId) {
        const response = await fetch(`${API_BASE_URL}/books/${selectedBook.id}/chapters/${chapterId}`);
        if (response.ok) {
          const scenes = await response.json();
          // Get API base from loadBookData
          const API_BASE_URL_FROM_ENV = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';
          const sceneSegments = scenes.map((scene: any) => ({
            ...scene,
            image_file: scene.image_file.startsWith('http')
              ? scene.image_file
              : `${API_BASE_URL_FROM_ENV}/books/${selectedBook.id}/images/${scene.image_file}`
          }));
          
          data = {
            chapters: [],
            characterImages: {},
            environmentImages: {},
            sceneSegments
          };
        }
      }
      
      // Fallback to load from book-level scenes
      if (!data) {
        data = await loadBookData(selectedBook.id);
      }
      
      setBookData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load book data');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToLibrary = () => {
    setSelectedBook(null);
    setSelectedChapter(null);
    setBookData(null);
    setError(null);
  };

  const handleBackToChapters = () => {
    setSelectedChapter(null);
    setBookData(null);
    setError(null);
  };

  // Show book chooser if no book is selected
  if (!selectedBook) {
    return <BookChooser onBookSelect={handleBookSelect} />;
  }

  // Show chapter chooser if no chapter is selected
  if (!selectedChapter) {
    return (
      <ChapterChooser 
        bookId={selectedBook.id}
        bookTitle={selectedBook.title}
        onChapterSelect={handleChapterSelect}
        onBack={handleBackToLibrary}
      />
    );
  }

  // Show loading state
  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>Loading chapter...</p>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="app-error">
        <h2>Error Loading Chapter</h2>
        <p>{error}</p>
        <div className="error-actions">
          <button onClick={() => handleChapterSelect(selectedChapter)}>
            Try Again
          </button>
          <button onClick={handleBackToChapters}>
            Back to Chapters
          </button>
        </div>
      </div>
    );
  }

  // Show book reader
  if (!bookData) {
    return (
      <div className="app-error">
        <h2>No Chapter Data</h2>
        <p>Unable to load chapter data.</p>
        <button onClick={handleBackToChapters}>
          Back to Chapters
        </button>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="app-header">
        <button className="back-button" onClick={handleBackToChapters}>
          ← Back to Chapters
        </button>
        <h1 className="book-title">{selectedBook.title}</h1>
      </div>
      <BookReader bookData={bookData} />
    </div>
  );
}

export default App;
