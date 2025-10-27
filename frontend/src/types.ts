export interface Character {
  name: string;
  description: string;
}

export interface Scene {
  scene_description: string;
  mood_description: string;
  characters: Character[];
  significant_objects: Array<{
    name: string;
    description: string;
  }>;
}

export interface Chapter {
  chapter_title: string;
  chapter_number: number;
  scene_description: string;
  mood_description: string;
  characters: Character[];
  significant_objects: Array<{
    name: string;
    description: string;
  }>;
}

export interface BookData {
  chapters: Chapter[];
  characterImages: { [key: string]: string };
  environmentImages: { [key: string]: string };
  sceneSegments: SceneSegment[];
}

export interface TextBlock {
  text: string;
  type: 'narration' | 'dialogue';
  speaker?: string;
  mentionedCharacter?: string;
  imageType: 'character' | 'environment' | 'scene' | 'action';
  imageName: string;
  sceneTitle?: string;
  setting?: string;
  mood?: string;
  charactersPresent?: string[];
}

export interface SceneSegment {
  scene_number: number;
  title: string;
  content: string;
  characters_present: string[];
  setting: string;
  mood: string;
  image_prompt: string;
  image_type: string;
  image_file: string;
}
