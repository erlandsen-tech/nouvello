import React, { useState, useEffect } from 'react';
import { BookData, TextBlock, SceneSegment } from '../types';
import TextPanel from './TextPanel';
import ImagePanel from './ImagePanel';
import Navigation from './Navigation';
import './BookReader.css';

interface BookReaderProps {
  bookData: BookData;
}

const BookReader: React.FC<BookReaderProps> = ({ bookData }) => {
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);
  const [textBlocks, setTextBlocks] = useState<TextBlock[]>([]);

  // Use scene segments instead of parsing chapter content
  useEffect(() => {
    if (!bookData.sceneSegments || bookData.sceneSegments.length === 0) return;

    const blocks = convertScenesToTextBlocks(bookData.sceneSegments);
    setTextBlocks(blocks);
    setCurrentSceneIndex(0);
  }, [bookData.sceneSegments]);

  const convertScenesToTextBlocks = (scenes: SceneSegment[]): TextBlock[] => {
    return scenes.map((scene, index) => {
      // Create a more reliable image name that matches the generated files
      const sceneNumber = String(index + 1).padStart(2, '0');
      const cleanTitle = scene.title.toLowerCase()
        .replace(/[^\w\s-]/g, '') // Remove special characters but keep hyphens
        .replace(/\s+/g, '_')     // Replace spaces with underscores
        .replace(/-/g, '_')       // Replace hyphens with underscores
        .trim();
      
      const imageName = `${sceneNumber}_${cleanTitle}`;
      
      return {
        text: scene.content,
        type: 'narration' as const,
        imageType: 'scene', // Force all scene images to use 'scene' type
        imageName,
        sceneTitle: scene.title,
        setting: scene.setting,
        mood: scene.mood,
        charactersPresent: scene.characters_present
      };
    });
  };

  const currentBlock = textBlocks[currentSceneIndex];
  const totalBlocks = textBlocks.length;

  const nextBlock = () => {
    if (currentSceneIndex < totalBlocks - 1) {
      setCurrentSceneIndex(currentSceneIndex + 1);
    }
  };

  const prevBlock = () => {
    if (currentSceneIndex > 0) {
      setCurrentSceneIndex(currentSceneIndex - 1);
    }
  };

  if (!currentBlock) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="book-reader">
      <div className="book-header">
        <h1>{currentBlock.sceneTitle || 'Alice in Wonderland'}</h1>
        <div className="progress">
          Scene {currentSceneIndex + 1} of {totalBlocks}
          {currentBlock.setting && ` • ${currentBlock.setting}`}
        </div>
      </div>
      
      <div className="book-content">
        <TextPanel 
          text={currentBlock.text}
          type={currentBlock.type}
          speaker={currentBlock.speaker}
          sceneTitle={currentBlock.sceneTitle}
          mood={currentBlock.mood}
        />
        <ImagePanel 
          imageType={currentBlock.imageType}
          imageName={currentBlock.imageName}
          bookData={bookData}
        />
      </div>
      
      <Navigation 
        onNext={nextBlock}
        onPrev={prevBlock}
        canGoNext={currentSceneIndex < totalBlocks - 1}
        canGoPrev={currentSceneIndex > 0}
      />
    </div>
  );
};

export default BookReader;
