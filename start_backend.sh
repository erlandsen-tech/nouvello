#!/bin/bash
# Start the Flask backend server using .venv

PROJECT_ROOT="$(dirname "$0")"
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found. Please create it first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  uv pip install -r requirements.txt"
    exit 1
fi

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing dependencies from requirements.txt..."
    uv pip install -r requirements.txt || python -m pip install -r requirements.txt
fi

# Start the backend
cd backend
python api.py

