import React from 'react';
import './TextPanel.css';

interface TextPanelProps {
  text: string;
  type: 'narration' | 'dialogue';
  speaker?: string;
  sceneTitle?: string;
  mood?: string;
}

const TextPanel: React.FC<TextPanelProps> = ({ text, type, speaker, sceneTitle, mood }) => {
  return (
    <div className="text-panel">
      <div className="text-content">
        {sceneTitle && (
          <div className="scene-title">{sceneTitle}</div>
        )}
        {mood && (
          <div className="scene-mood">{mood}</div>
        )}
        {type === 'dialogue' && speaker && (
          <div className="speaker-name">{speaker}</div>
        )}
        <div className={`text-block ${type}`}>
          {text}
        </div>
      </div>
    </div>
  );
};

export default TextPanel;
