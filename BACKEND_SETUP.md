# Backend Setup

## Overview

The backend Flask API serves book data and images directly from the `output/` folder. This eliminates the need to duplicate files in the frontend.

## Architecture

```
output/
├── alice/
│   ├── scenes.json           # Scene definitions
│   ├── consistent_scenes/    # Generated images
│   ├── character_prompts.json
│   └── analysis.json
└── peterpan/
    ├── scenes.json
    ├── consistent_scenes/
    ├── character_prompts.json
    └── analysis.json
```

## API Endpoints

### GET /api/books
Returns list of all books by scanning the `output/` directory.

**Response:**
```json
[
  {
    "id": "alice",
    "title": "Alice",
    "description": "Visual novel adaptation of Alice",
    "data_dir": "alice",
    "created_at": "",
    "scenes_count": 12,
    "characters_count": 4
  }
]
```

### GET /api/books/{book_id}/scenes
Returns the `scenes.json` file for a specific book.

**Response:**
```json
[
  {
    "scene_number": 1,
    "title": "Scene Title",
    "content": "Scene text...",
    "characters_present": ["Alice"],
    "setting": "...",
    "mood": "...",
    "image_type": "scene",
    "image_file": "scene_01_title.png"
  }
]
```

### GET /api/books/{book_id}/images/{image_path}
Serves an image file from:
1. `output/{book_id}/consistent_scenes/{image_path}` (primary)
2. `output/{book_id}/scenes/{image_path}` (fallback)
3. `output/{book_id}/images/{image_path}` (fallback)

Returns PNG image binary data.

### DELETE /api/books/{book_id}
Deletes a book and all its data from the `output/` directory.

## Running the Backend

```bash
cd backend
python api.py
```

The server runs on `http://localhost:5000`

## Frontend Integration

The frontend automatically discovers and displays all books found in `output/`:
- Fetches book list from `/api/books`
- Loads scenes from `/api/books/{id}/scenes`
- Displays images via `/api/books/{id}/images/{filename}`

No manual configuration needed when adding new books!

