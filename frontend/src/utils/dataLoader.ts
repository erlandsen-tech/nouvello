import { BookData, Chapter, SceneSegment } from '../types';

export const loadBookData = async (bookId: string): Promise<BookData> => {
  try {
    // Load analysis data
    const analysisResponse = await fetch(`/data/${bookId}/analysis.json`);
    const analysisData: Chapter[] = await analysisResponse.json();

    // Load character prompts for image mapping
    const characterPromptsResponse = await fetch(`/data/${bookId}/character_prompts.json`);
    const characterPrompts = await characterPromptsResponse.json();

    // Load scene segments
    const scenesResponse = await fetch(`/data/${bookId}/scenes.json`);
    const sceneSegments: SceneSegment[] = await scenesResponse.json();

    // Create character image mapping
    const characterImages: { [key: string]: string } = {};
    if (characterPrompts.characters) {
      characterPrompts.characters.forEach((char: any) => {
        const imageName = char.name.replace(/'/g, '').replace(/\s+/g, '_');
        characterImages[imageName] = `/images/characters/${imageName}.png`;
      });
    }

    // Create environment image mapping
    const environmentImages: { [key: string]: string } = {
      'chapter_i_down_the_rabbit_hole': '/images/environments/chapter_i_down_the_rabbit_hole.png'
    };

    return {
      chapters: analysisData,
      characterImages,
      environmentImages,
      sceneSegments
    };
  } catch (error) {
    console.error('Error loading book data:', error);
    throw error;
  }
};
