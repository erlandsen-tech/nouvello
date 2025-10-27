import React, { useState, useEffect } from 'react';
import BookReader from './components/BookReader';
import BookChooser from './components/BookChooser';
import { BookData } from './types';
import { loadBookData } from './utils/dataLoader';
import './App.css';

function App() {
  const [selectedBook, setSelectedBook] = useState<string | null>(null);
  const [bookData, setBookData] = useState<BookData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBookSelect = async (bookId: string) => {
    setSelectedBook(bookId);
    setLoading(true);
    setError(null);
    
    try {
      const data = await loadBookData(bookId);
      setBookData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load book data');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToLibrary = () => {
    setSelectedBook(null);
    setBookData(null);
    setError(null);
  };

  // Show book chooser if no book is selected
  if (!selectedBook) {
    return <BookChooser onBookSelect={handleBookSelect} />;
  }

  // Show loading state
  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>Loading {selectedBook}...</p>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="app-error">
        <h2>Error Loading Book</h2>
        <p>{error}</p>
        <div className="error-actions">
          <button onClick={() => handleBookSelect(selectedBook)}>
            Try Again
          </button>
          <button onClick={handleBackToLibrary}>
            Back to Library
          </button>
        </div>
      </div>
    );
  }

  // Show book reader
  if (!bookData) {
    return (
      <div className="app-error">
        <h2>No Book Data</h2>
        <p>Unable to load book data.</p>
        <button onClick={handleBackToLibrary}>
          Back to Library
        </button>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="app-header">
        <button className="back-button" onClick={handleBackToLibrary}>
          ← Back to Library
        </button>
        <h1 className="book-title">{selectedBook.replace('_', ' ').toUpperCase()}</h1>
      </div>
      <BookReader bookData={bookData} />
    </div>
  );
}

export default App;