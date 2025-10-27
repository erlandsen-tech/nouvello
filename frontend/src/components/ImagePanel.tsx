import React from 'react';
import { BookData } from '../types';
import './ImagePanel.css';

interface ImagePanelProps {
  imageType: 'character' | 'environment' | 'scene' | 'action';
  imageName: string;
  bookData: BookData;
}

const ImagePanel: React.FC<ImagePanelProps> = ({ imageType, imageName, bookData }) => {
  const getImagePath = () => {
    switch (imageType) {
      case 'character':
        return `/images/characters/${imageName}.png`;
      case 'environment':
        return `/images/environments/${imageName}.png`;
      case 'scene':
      case 'action':
        // Use the imageName directly since it's now formatted as "01_bored_by_the_bank"
        return `/images/scenes/scene_${imageName}.png`;
      default:
        return `/images/environments/chapter_i_down_the_rabbit_hole.png`;
    }
  };

  const imagePath = getImagePath();

  return (
    <div className="image-panel">
      <div className="image-container">
        <img 
          src={imagePath} 
          alt={imageName}
          className="book-image"
          onError={(e) => {
            // Fallback to environment image if scene/action image not found
            if (imageType === 'scene' || imageType === 'action') {
              (e.target as HTMLImageElement).src = '/images/environments/chapter_i_down_the_rabbit_hole.png';
            } else if (imageType === 'character') {
              (e.target as HTMLImageElement).src = '/images/environments/chapter_i_down_the_rabbit_hole.png';
            }
          }}
        />
      </div>
    </div>
  );
};

export default ImagePanel;
