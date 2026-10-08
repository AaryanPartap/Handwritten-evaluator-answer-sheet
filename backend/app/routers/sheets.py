import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from app.models.schemas import SheetUploadResponse, Sheet, UserProfile
from app.services.firebase_service import db_service
from app.auth.security import get_current_user

router = APIRouter(prefix="/sheets", tags=["Answer Sheets"])

@router.post("/upload", response_model=SheetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_sheet(
    image: UploadFile = File(...),
    roll_no: str = Form(...),
    question_id: str = Form(...),
    subject: str = Form("Computer Science"),
    rubric_id: Optional[str] = Form(None),
    user: UserProfile = Depends(get_current_user)
):
    """
    Uploads a scanned student answer sheet, tags with roll no and question id.
    Saves image in Firebase Storage or local upload folder.
    """
    sheet_id = f"sheet_{uuid.uuid4().hex[:8]}"
    file_ext = image.filename.split(".")[-1] if "." in image.filename else "jpg"
    filename = f"{sheet_id}.{file_ext}"
    
    file_bytes = await image.read()
    image_url = db_service.save_image(filename, file_bytes)
    now_iso = datetime.now(timezone.utc).isoformat()
    
    sheet_data = {
        "id": sheet_id,
        "roll_no": roll_no.strip(),
        "question_id": question_id.strip(),
        "rubric_id": rubric_id.strip() if rubric_id else None,
        "subject": subject.strip(),
        "image_url": image_url,
        "raw_ocr_text": None,
        "corrected_text": None,
        "status": "uploaded",
        "created_at": now_iso,
        "created_by": user.email
    }
    
    db_service.save_sheet(sheet_id, sheet_data)
    
    return SheetUploadResponse(
        sheet_id=sheet_id,
        image_url=image_url,
        roll_no=roll_no,
        question_id=question_id,
        rubric_id=rubric_id,
        subject=subject,
        status="uploaded"
    )

@router.get("/{sheet_id}", response_model=Sheet)
def get_sheet(sheet_id: str, user: UserProfile = Depends(get_current_user)):
    """
    Fetches a sheet record by ID.
    """
    sheet = db_service.get_sheet(sheet_id)
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet with ID '{sheet_id}' not found"
        )
    return Sheet(**sheet)

@router.get("", response_model=List[Sheet])
def list_sheets(question_id: Optional[str] = None, user: UserProfile = Depends(get_current_user)):
    """
    Lists uploaded sheets, optionally filtered by question_id.
    """
    sheets = db_service.list_sheets(question_id=question_id)
    return [Sheet(**s) for s in sheets]
