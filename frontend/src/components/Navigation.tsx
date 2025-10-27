import React from 'react';
import './Navigation.css';

interface NavigationProps {
  onNext: () => void;
  onPrev: () => void;
  canGoNext: boolean;
  canGoPrev: boolean;
}

const Navigation: React.FC<NavigationProps> = ({ onNext, onPrev, canGoNext, canGoPrev }) => {
  return (
    <div className="navigation">
      <button 
        className="nav-button prev" 
        onClick={onPrev}
        disabled={!canGoPrev}
      >
        ← Previous
      </button>
      
      <div className="nav-spacer"></div>
      
      <button 
        className="nav-button next" 
        onClick={onNext}
        disabled={!canGoNext}
      >
        Next →
      </button>
    </div>
  );
};

export default Navigation;
