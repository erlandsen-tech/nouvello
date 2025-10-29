import React, { useState, useEffect } from 'react';
import './ChapterChooser.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

interface Chapter {
  id: string;
  title: string;
  number: number | null;
  preview_image?: string | null;
}

interface ChapterChooserProps {
  bookId: string;
  bookTitle: string;
  onChapterSelect: (chapterId: string) => void;
  onBack: () => void;
}

const ChapterChooser: React.FC<ChapterChooserProps> = ({ bookId, bookTitle, onChapterSelect, onBack }) => {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadChapters();
  }, [bookId]);

  const loadChapters = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/books/${bookId}/chapters`);
      if (!response.ok) {
        throw new Error('Failed to load chapters');
      }
      const data = await response.json();
      setChapters(data.chapters || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chapters');
    } finally {
      setLoading(false);
    }
  };

  const handleChapterSelect = (chapterId: string) => {
    onChapterSelect(chapterId);
  };

  if (loading) {
    return (
      <div className="chapter-chooser">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading chapters...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chapter-chooser">
        <div className="error-container">
          <h2>Error Loading Chapters</h2>
          <p>{error}</p>
          <button onClick={loadChapters}>Try Again</button>
          <button onClick={onBack}>Back to Books</button>
        </div>
      </div>
    );
  }

  // If no chapters available, show message
  if (chapters.length === 0) {
    return (
      <div className="chapter-chooser">
        <div className="chapter-chooser-header">
          <button className="back-button" onClick={onBack}>
            ← Back to Library
          </button>
          <h1>{bookTitle}</h1>
        </div>
        <div className="no-chapters-container">
          <h2>No Chapters Available</h2>
          <p>This book doesn't have individual chapters configured yet.</p>
          <p>The current implementation requires per-chapter scene files.</p>
          <button onClick={onBack} className="back-to-library-button">
            ← Back to Library
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="chapter-chooser">
      <div className="chapter-chooser-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Library
        </button>
        <h1>{bookTitle}</h1>
        <p>Choose a chapter to read</p>
      </div>
      
      <div className="chapters-list">
        {chapters.map((chapter) => (
          <div 
            key={chapter.id} 
            className="chapter-card"
            onClick={() => handleChapterSelect(chapter.id)}
          >
            {chapter.preview_image && (
              <div className="chapter-preview">
                <img 
                  src={chapter.preview_image} 
                  alt={`${chapter.title} preview`}
                  className="chapter-preview-image"
                />
              </div>
            )}
            <div className="chapter-info">
              {chapter.number && (
                <div className="chapter-number">Chapter {chapter.number}</div>
              )}
              <h3 className="chapter-title">{chapter.title}</h3>
            </div>
            <div className="chapter-action">
              <button className="read-button">Read</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChapterChooser;

