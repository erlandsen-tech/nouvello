import { BookData, SceneSegment } from '../types';

// Get API URL from environment variable, fallback to default
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

// Standardized loader: fetches scenes from backend API which reads from output/ folder
export const loadBookData = async (bookId: string): Promise<BookData> => {
  try {
    const scenesResponse = await fetch(`${API_BASE_URL}/books/${bookId}/scenes`);
    if (!scenesResponse.ok) {
      throw new Error(`Failed to load scenes for ${bookId}`);
    }
    const rawScenes: SceneSegment[] = await scenesResponse.json();

    // Normalize image_file to backend API URLs
    const sceneSegments: SceneSegment[] = rawScenes.map((scene) => ({
      ...scene,
      image_file: scene.image_file.startsWith('http')
        ? scene.image_file
        : `${API_BASE_URL}/books/${bookId}/images/${scene.image_file}`
    }));

    return {
      chapters: [],
      characterImages: {},
      environmentImages: {},
      sceneSegments
    };
  } catch (error) {
    console.error('Error loading book data:', error);
    throw error;
  }
};
