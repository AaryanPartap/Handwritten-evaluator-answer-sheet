# Handwritten Answer Evaluator (MVP)

A rubric-based evaluation system for handwritten student answer sheets combining OCR, fine-grained rubric conditioning, and an LLM evaluator with a faculty-in-the-loop review dashboard.

 


---

## 1. Architecture Overview

```
[ Faculty Browser ]
        │  HTML forms, sessions
        ▼
[ Flask Frontend: Port 5000 ]  (Thin server-rendered UI: login, rubric builder, upload, review, results)
        │  REST calls, Bearer Token
        ▼
[ FastAPI Backend: Port 8000 ] (Application brain: /auth, /rubrics, /sheets, /ocr, /evaluate, /scores)
   ├── OpenCV Preprocessing (Grayscale, adaptive threshold, deskew)
   ├── OCR Engine (TrOCR / Google Cloud Vision / Heuristic OCR)
   ├── LLM Evaluator (Gemini API with structured JSON output & temperature 0)
   └── Firebase Layer (Firestore NoSQL records & Storage for raw scan images / local fallback)
```

- **Flask Frontend (Port 5000):** Kept intentionally thin for rapid faculty interactions, rendering Jinja2 templates, holding authentication tokens in session, and delegating all business logic to FastAPI.
- **FastAPI Backend (Port 8000):** Exposes async endpoints, Pydantic data validation, OpenAPI docs at `/docs`, OCR image preprocessing, and structured LLM evaluation calls.
- **Firebase / Local Hybrid Mode:** Operates out of the box with zero external setup using local storage and simulated Firestore store (`backend/data/firestore_mock_store.json`), and automatically switches to live Firebase Auth, Firestore, and Cloud Storage whenever credentials are configured in `.env`.
- **LLM Evaluator:** Evaluates answers against fine-grained checklist rubrics returning structured JSON: marks, matched points with evidence quotes, missing points with deduction reasons, feedback, and confidence.

---

## 2. Directory Structure

```
Handwritten_Evaluator/
├── backend/
│   ├── app/
│   │   ├── auth/           # Firebase token verification & JWT security
│   │   ├── models/         # Pydantic schemas (Rubric, Sheet, Score, OCR, Evaluate)
│   │   ├── routers/        # API endpoints: auth, rubrics, sheets, ocr, evaluate, scores
│   │   ├── services/       # Firebase/DB service, OpenCV OCR pipeline, Gemini LLM evaluator
│   │   ├── config.py       # Configuration and environment variables
│   │   └── main.py         # FastAPI application entry point with CORS
│   └── data/               # Persistent data store (offline / local fallback)
├── frontend/
│   ├── static/             # Rich CSS styling and interactive JavaScript
│   ├── templates/          # Jinja2 templates (login, rubrics, upload, review, results)
│   ├── app.py              # Flask frontend server
│   └── config.py           # Frontend configuration
├── uploads/                # Scanned image files storage
├── run_backend.py          # FastAPI backend runner script
├── run_frontend.py         # Flask frontend runner script
├── run_all.py              # Unified single-command launcher
├── requirements.txt        # Python dependencies
└── .env                    # Environment configuration
```

---

## 3. Quick Start Guide

### Step 1: Activate Virtual Environment
```bash
source venv/bin/activate
```

### Step 2: (Optional) Set your Gemini API Key
To enable live AI evaluations via Google Gemini, open `.env` and provide your key:
```ini
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```
*(Note: If no API key is provided, the system seamlessly runs an intelligent rule-based rubric evaluator fallback for local testing).*

### Step 3: Run Both Servers Concurrently
```bash
python3 run_all.py
```

- **Faculty Web Dashboard:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **FastAPI Interactive API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 4. Core User Workflow

1. **Sign In (`/login`):** Use your faculty email or click **One-Click Demo Access**.
2. **Define Rubric (`/rubrics/new`):**
   - Enter the question and reference model answer.
   - Click **Load Sample Rubric (BFS)** or create checklist points with allocated sub-marks.
3. **Upload Answer Sheet (`/upload`):**
   - Enter student roll number (e.g. `21103042`) and question ID.
   - Select the target rubric.
   - Upload a scanned answer image (a pre-generated sample is provided at `uploads/sample_bfs_answer.jpg`).
   - The system automatically uploads the scan and executes the OpenCV + OCR transcription pipeline.
4. **Side-by-Side Review (`/review/<sheet_id>`):**
   - **Left:** Original handwritten answer image with pan/zoom controls.
   - **Center:** Editable OCR transcription. Faculty can refine text and click **Save Corrected Text** to ensure OCR artifacts never lead to unfair penalties.
   - **Right:** Click **Run LLM Evaluation** to obtain:
     - Suggested numeric score
     - Self-reported confidence rating (%)
     - Matched criteria with cited evidence quotes
     - Missing criteria with deduction rationale
     - Constructive feedback paragraph
   - **Approve or Override:** Faculty can accept or override marks, provide an audit reason, and click **Approve & Save Final Score**.
5. **Results & Analytics (`/results`):**
   - Review class-wide statistics: total submissions, average score, and LLM-faculty agreement rate.
   - Download complete marksheet via **Export CSV**.
