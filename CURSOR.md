# Python Environment
**ALWAYS USE THE .venv VIRTUAL ENVIRONMENT**
- Activate: `source .venv/bin/activate` (or `.venv/Scripts/activate` on Windows)
- Install dependencies: `uv pip install -r requirements.txt` or `python -m pip install -r requirements.txt`
- All Python dependencies are in `requirements.txt` at the project root
- Package management: Use `uv pip` or `python -m pip` (NOT bare `pip`)

# Backend Server
- Backend runs on **port 5001** by default (not 5000 - macOS Control Center uses that)
- Configuration via environment variables (see `.env.example`)
- Start: `./start_backend.sh` or `cd backend && python api.py`
- Backend config: `backend/config.py` (reads from `.env`)
- Frontend config: Uses `REACT_APP_API_URL` from `.env` (defaults to `http://localhost:5001/api`)

# Environment Variables
- Copy `.env.example` to `.env` to customize configuration
- Backend: `FLASK_PORT`, `FLASK_HOST`, `CORS_ORIGINS`, `FLASK_DEBUG`
- Frontend: `REACT_APP_API_URL`
- **DO NOT** hardcode URLs or ports in code - use environment variables

# Dependencies
- Use UV -> `uv pip install`, `uv pip uninstall`
- Requirements file: `requirements.txt` (root directory)
- Backend requires: flask, flask-cors, boto3, ebooklib, beautifulsoup4, Pillow, google-genai
- Frontend requires: Node.js packages (see `frontend/package.json`)

# Cursor AI Rules for this project

## Documentation Policy
- DO NOT create documentation files (*.md, README files) unless explicitly requested by the user
- DO NOT create guide files, quickstart files, or tutorial files proactively
- Focus on code implementation, not documentation
- If the user asks "how to use X", explain in the chat response, don't create markdown files

## Code Focus
- Prioritize working code over documentation
- Create code examples in demos or test files, not markdown
- Use inline comments and docstrings for code documentation
- Only create markdown if user explicitly says "create a README" or "write documentation"

## File Creation
- Ask before creating helper/wrapper scripts if the core functionality works
- Don't create multiple variations of the same tool unless requested
- Keep it simple and focused on what the user asked for

## Communication
- Explain usage in chat responses
- Show code examples in chat using code blocks
- Don't create files to explain things that can be explained in chat

## Running Python Code
- **ALWAYS USE .venv** - Activate before running any Python commands
- Use `python -m pip` or `uv pip` for package management
- All dependencies must be in `requirements.txt`
- Check venv is active: `which python` should show `.venv/bin/python`