import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from app.models.schemas import RubricCreate, Rubric, UserProfile
from app.services.firebase_service import db_service
from app.auth.security import get_current_user

router = APIRouter(prefix="/rubrics", tags=["Rubrics"])

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_rubric(payload: RubricCreate, user: UserProfile = Depends(get_current_user)):
    """
    Creates a new evaluation rubric with discrete checklist points.
    Returns rubric_id.
    """
    rubric_id = f"rubric_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    
    rubric_data = {
        "id": rubric_id,
        "question_text": payload.question_text,
        "model_answer": payload.model_answer,
        "max_marks": payload.max_marks,
        "rubric_points": [p.model_dump() for p in payload.rubric_points],
        "subject": payload.subject or "General",
        "created_by": user.email,
        "created_at": now_iso
    }
    
    saved_id = db_service.save_rubric(rubric_id, rubric_data)
    return {
        "rubric_id": saved_id,
        "message": "Rubric created successfully",
        "status": "created"
    }

@router.get("/{rubric_id}", response_model=Rubric)
def get_rubric(rubric_id: str, user: UserProfile = Depends(get_current_user)):
    """
    Retrieves a rubric by its ID.
    """
    rubric = db_service.get_rubric(rubric_id)
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rubric with ID '{rubric_id}' not found"
        )
    return Rubric(**rubric)

@router.get("", response_model=List[Rubric])
def list_rubrics(user: UserProfile = Depends(get_current_user)):
    """
    Lists all saved rubrics.
    """
    rubrics = db_service.list_rubrics()
    return [Rubric(**r) for r in rubrics]
