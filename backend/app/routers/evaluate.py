from fastapi import APIRouter, HTTPException, Depends, status
from app.models.schemas import EvaluateRequest, EvaluationResponse, UserProfile
from app.services.firebase_service import db_service
from app.services.evaluator_service import evaluator_service
from app.auth.security import get_current_user

router = APIRouter(prefix="/evaluate", tags=["Evaluation Service"])

@router.post("/{sheet_id}", response_model=EvaluationResponse)
def evaluate_sheet(
    sheet_id: str,
    payload: EvaluateRequest,
    user: UserProfile = Depends(get_current_user)
):
    """
    Evaluates the student's answer against the given rubric using LLM structured output.
    Returns suggested marks, matched/missing points, feedback, and confidence.
    """
    sheet = db_service.get_sheet(sheet_id)
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet with ID '{sheet_id}' not found"
        )

    rubric = db_service.get_rubric(payload.rubric_id)
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rubric with ID '{payload.rubric_id}' not found"
        )

    student_text = sheet.get("corrected_text") or sheet.get("raw_ocr_text")
    if not student_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extracted text found for this sheet. Please run OCR first."
        )

    # Call LLM Evaluator
    eval_result = evaluator_service.evaluate(rubric, student_text)

    # Update sheet status and attach rubric_id
    db_service.update_sheet(sheet_id, {
        "rubric_id": payload.rubric_id,
        "status": "evaluated"
    })

    return eval_result
