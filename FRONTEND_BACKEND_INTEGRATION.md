# Frontend-Backend Integration

## Architecture Overview

The application now uses a **single source of truth** for all book data: the `output/` folder.

```
output/                    ← Single source of truth
├── alice/
│   ├── scenes.json       ← Scene definitions with text & image refs
│   └── consistent_scenes/ ← Generated scene images
│       ├── scene_01_bored_by_the_bank.png
│       ├── scene_02_the_white_rabbit_appears.png
│       └── ...
└── peterpan/
    ├── scenes.json
    └── consistent_scenes/
        ├── scene_01_the_boy_at_the_window.png
        └── ...

Backend (Flask) ────────────► Scans output/ dynamically
     │                        Serves JSON & images via REST API
     │
     ▼
Frontend (React) ───────────► Fetches data from backend API
                               No file duplication needed!
```

## Data Flow

### 1. Book Generation → Output Folder
When you generate a book, all files go to `output/{book_name}/`:
- `scenes.json` - Scene text and image references
- `consistent_scenes/*.png` - Generated scene images
- `character_prompts.json` - Character definitions
- `analysis.json` - Book metadata

### 2. Backend Auto-Discovery
The Flask backend (`backend/api.py`) automatically:
- Scans `output/` for all subdirectories
- Finds books with `scenes.json`
- Extracts metadata (scene count, character count)
- Serves via REST API

### 3. Frontend Display
The React frontend:
- Calls `/api/books` to list all available books
- Calls `/api/books/{id}/scenes` to load scene data
- Displays images via `/api/books/{id}/images/{filename}`

## Key Files

### Backend
- `backend/api.py` - Flask REST API server
- `start_backend.sh` - Start script for backend

### Frontend
- `frontend/src/utils/dataLoader.ts` - API client
- `frontend/src/components/BookChooser.tsx` - Book library UI
- `frontend/src/components/BookReader.tsx` - Reading interface
- `frontend/src/components/ImagePanel.tsx` - Image display

## Running the Application

### 1. Install Dependencies
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Start Backend
```bash
./start_backend.sh
# OR
cd backend && python3 api.py
```
Backend runs on `http://localhost:5000`

### 3. Start Frontend
```bash
cd frontend
npm start
```
Frontend runs on `http://localhost:3000`

### 4. Generate a Book
```bash
python book_to_vn.py path/to/your/book.epub
```

The book will automatically appear in the frontend without any manual steps!

## Adding a New Book

1. Run your book generation pipeline
2. Ensure output structure:
   ```
   output/{book_name}/
   ├── scenes.json           ← Required
   └── consistent_scenes/    ← Required
       └── *.png
   ```
3. Refresh the frontend
4. Book appears automatically!

## Benefits

✅ **Single Source of Truth** - No file duplication  
✅ **Auto-Discovery** - Books appear automatically  
✅ **Scalable** - Works for any number of books  
✅ **Consistent** - Same structure for generation and display  
✅ **Easy to Debug** - All data in one place (`output/`)  

## Troubleshooting

### "Failed to load books"
- Ensure backend is running on port 5000
- Check `output/` folder exists
- Verify at least one book has `scenes.json`

### Images not loading
- Check `consistent_scenes/` folder exists
- Verify image filenames match `scenes.json`
- Check browser console for 404 errors

### Book not appearing
- Verify `scenes.json` exists in `output/{book_name}/`
- Check JSON is valid
- Restart backend to rescan

