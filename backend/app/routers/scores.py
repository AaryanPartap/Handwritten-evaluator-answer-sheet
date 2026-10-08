from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from app.models.schemas import ApproveScoreRequest, Score, StatusResponse, UserProfile, ResultSummaryItem
from app.services.firebase_service import db_service
from app.auth.security import get_current_user

router = APIRouter(tags=["Scores & Results"])

@router.post("/scores/{sheet_id}/approve", response_model=StatusResponse)
def approve_score(
    sheet_id: str,
    payload: ApproveScoreRequest,
    user: UserProfile = Depends(get_current_user)
):
    """
    Finalizes and saves the grade for a student's answer sheet.
    Logs if faculty overrode/edited the suggested mark and records audit trail.
    """
    sheet = db_service.get_sheet(sheet_id)
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet with ID '{sheet_id}' not found"
        )

    rubric_id = sheet.get("rubric_id")
    rubric = db_service.get_rubric(rubric_id) if rubric_id else None
    max_marks = float(rubric.get("max_marks", payload.final_marks)) if rubric else payload.final_marks

    # Check if there is existing evaluation data or draft score
    existing_score = db_service.get_score(sheet_id) or {}
    now_iso = datetime.now(timezone.utc).isoformat()

    score_data = {
        "sheet_id": sheet_id,
        "roll_no": sheet.get("roll_no", "UNKNOWN"),
        "question_id": sheet.get("question_id", "Q1"),
        "rubric_id": rubric_id or "unassigned",
        "suggested_marks": existing_score.get("suggested_marks", payload.final_marks),
        "max_marks": max_marks,
        "matched_points": existing_score.get("matched_points", []),
        "missing_points": existing_score.get("missing_points", []),
        "feedback": existing_score.get("feedback", "Graded and approved by faculty."),
        "confidence": existing_score.get("confidence", 1.0),
        "final_marks": payload.final_marks,
        "edited_flag": payload.edited_flag,
        "override_reason": payload.override_reason,
        "approved_by": user.email,
        "approved_at": now_iso
    }

    db_service.save_score(sheet_id, score_data)

    return StatusResponse(
        status="saved",
        message=f"Score of {payload.final_marks}/{max_marks} successfully finalized and saved"
    )

@router.get("/scores/{sheet_id}", response_model=Score)
def get_score(sheet_id: str, user: UserProfile = Depends(get_current_user)):
    """
    Retrieves finalized score record for a sheet.
    """
    score = db_service.get_score(sheet_id)
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No finalized score found for sheet ID '{sheet_id}'"
        )
    return Score(**score)

@router.get("/results", response_model=List[ResultSummaryItem])
def get_results(
    question_id: Optional[str] = Query(None, description="Optional question ID filter"),
    user: UserProfile = Depends(get_current_user)
):
    """
    Returns list of all scored answers for a question (or all questions),
    ready for tabular display and CSV export.
    """
    scores = db_service.list_scores(question_id=question_id)
    results: List[ResultSummaryItem] = []

    for s in scores:
        results.append(ResultSummaryItem(
            sheet_id=s.get("sheet_id", ""),
            roll_no=s.get("roll_no", ""),
            question_id=s.get("question_id", ""),
            rubric_id=s.get("rubric_id", ""),
            final_marks=float(s.get("final_marks", 0)),
            max_marks=float(s.get("max_marks", 10)),
            suggested_marks=float(s.get("suggested_marks", 0)),
            edited_flag=bool(s.get("edited_flag", False)),
            confidence=float(s.get("confidence", 1.0)),
            approved_at=s.get("approved_at", ""),
            status="approved"
        ))

    return results
