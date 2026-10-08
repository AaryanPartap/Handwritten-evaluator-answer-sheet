import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_path))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting FastAPI Backend on http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    print(f"Interactive Swagger Docs available at http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}/docs")
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
