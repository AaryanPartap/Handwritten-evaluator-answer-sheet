import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

class FrontendConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "flask-secret-key-evaluator-pec-2026")
    BACKEND_URL = f"http://{os.getenv('BACKEND_HOST', '127.0.0.1')}:{os.getenv('BACKEND_PORT', '8000')}"
    FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5000"))
    
    # Firebase Web client configuration (for browser SDK when configured)
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
    FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN", "")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "")

frontend_config = FrontendConfig()
