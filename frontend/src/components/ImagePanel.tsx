import React from 'react';
import { BookData } from '../types';
import './ImagePanel.css';

interface ImagePanelProps {
  imageType: 'character' | 'environment' | 'scene' | 'action';
  imageName: string;
  imageUrl?: string;
  bookData: BookData;
}

const ImagePanel: React.FC<ImagePanelProps> = ({ imageType, imageName, imageUrl, bookData }) => {
  // All images should come from the backend API via imageUrl
  const imagePath = imageUrl || '';

  return (
    <div className="image-panel">
      <div className="image-container">
        <img 
          src={imagePath} 
          alt={imageName}
          className="book-image"
          onError={(e) => {
            const imgEl = e.target as HTMLImageElement;
            // Try to use first scene image from the current book as fallback
            const firstSceneUrl = bookData.sceneSegments && bookData.sceneSegments.length > 0
              ? bookData.sceneSegments[0].image_file
              : undefined;
            if (firstSceneUrl) {
              imgEl.src = firstSceneUrl;
            }
            // If still no image, just hide the broken image
            // (Could also set to a placeholder image here)
          }}
        />
      </div>
    </div>
  );
};

export default ImagePanel;
