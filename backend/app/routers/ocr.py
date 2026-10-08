from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, status
from app.models.schemas import OCRResponse, OCRPatchRequest, StatusResponse, UserProfile
from app.services.firebase_service import db_service
from app.services.ocr_service import ocr_service
from app.auth.security import get_current_user
from app.config import settings

router = APIRouter(prefix="/ocr", tags=["OCR Service"])

@router.post("/{sheet_id}", response_model=OCRResponse)
def run_ocr_on_sheet(sheet_id: str, user: UserProfile = Depends(get_current_user)):
    """
    Executes OpenCV preprocessing + OCR engine on the uploaded sheet image.
    Stores raw extracted text and confidence in Firestore / DB.
    """
    sheet = db_service.get_sheet(sheet_id)
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet with ID '{sheet_id}' not found"
        )

    # Determine local file path
    image_url = sheet.get("image_url", "")
    filename = Path(image_url).name
    image_path = settings.UPLOAD_DIR / filename

    if not image_path.exists():
        # If running in cloud or URL format, try fallback
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image file not found on server at {image_path}"
        )

    ocr_result = ocr_service.extract_text(image_path)
    raw_text = ocr_result["raw_text"]
    confidence = ocr_result["confidence"]

    # Persist in DB
    db_service.update_sheet(sheet_id, {
        "raw_ocr_text": raw_text,
        "corrected_text": raw_text,  # defaults to raw text until faculty edits
        "status": "ocr_completed"
    })

    return OCRResponse(
        sheet_id=sheet_id,
        raw_text=raw_text,
        confidence=confidence,
        status="ocr_completed"
    )

@router.patch("/{sheet_id}", response_model=StatusResponse)
def update_corrected_text(sheet_id: str, payload: OCRPatchRequest, user: UserProfile = Depends(get_current_user)):
    """
    Faculty updates or corrects the extracted OCR text before evaluation.
    This ensures noisy OCR never silently leads to an unfair mark.
    """
    sheet = db_service.get_sheet(sheet_id)
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet with ID '{sheet_id}' not found"
        )

    db_service.update_sheet(sheet_id, {
        "corrected_text": payload.corrected_text
    })

    return StatusResponse(
        status="updated",
        message="OCR text corrected successfully by faculty"
    )
