import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server configuration
FLASK_PORT = int(os.getenv('FLASK_PORT', 5001))
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"

# CORS
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')


