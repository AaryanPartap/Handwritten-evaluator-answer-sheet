from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routers import auth, rubrics, sheets, ocr, evaluate, scores

app = FastAPI(
    title="Handwritten Answer Evaluator API",
    description="Backend API for rubric-conditioned evaluation of handwritten student answers using OCR and LLMs.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded scanned images locally
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# Include functional routers
app.include_router(auth.router)
app.include_router(rubrics.router)
app.include_router(sheets.router)
app.include_router(ocr.router)
app.include_router(evaluate.router)
app.include_router(scores.router)

@app.get("/", tags=["General"])
def root_status():
    return {
        "project": "Handwritten Answer Evaluator",
        "status": "online",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "engine": {
            "ocr_engine": settings.OCR_ENGINE,
            "llm_model": settings.GEMINI_MODEL,
            "firebase_enabled": settings.USE_FIREBASE
        }
    }

@app.get("/health", tags=["General"])
def health_check():
    return {
        "status": "healthy",
        "firebase": "connected" if settings.USE_FIREBASE else "local_mock_mode",
        "llm_ready": bool(settings.GEMINI_API_KEY)
    }
