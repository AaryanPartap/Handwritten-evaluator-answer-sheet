from typing import List, Optional, Any
from pydantic import BaseModel, Field

# ----------------- Auth Schemas -----------------
class TokenVerifyRequest(BaseModel):
    token: str

class UserProfile(BaseModel):
    uid: str
    email: str
    name: str = "Faculty User"
    role: str = "faculty"

# ----------------- Rubric Schemas -----------------
class RubricPoint(BaseModel):
    id: str = Field(..., description="Unique ID for this rubric point item, e.g. 'pt_1'")
    text: str = Field(..., description="Criterion description or key expected element")
    marks: float = Field(..., description="Sub-marks allocated to this criterion")

class RubricCreate(BaseModel):
    question_text: str = Field(..., description="Question description or prompt")
    model_answer: str = Field(..., description="Ideal or reference answer")
    max_marks: float = Field(..., description="Total maximum score for this question")
    rubric_points: List[RubricPoint] = Field(..., description="List of discrete checklist points")
    subject: Optional[str] = Field("Data Structures & Algorithms", description="Subject name")

class Rubric(RubricCreate):
    id: str
    created_by: str = "faculty_demo"
    created_at: str

# ----------------- Sheet Schemas -----------------
class SheetUploadResponse(BaseModel):
    sheet_id: str
    image_url: str
    roll_no: str
    question_id: str
    rubric_id: Optional[str] = None
    subject: str = "General"
    status: str = "uploaded"

class Sheet(BaseModel):
    id: str
    roll_no: str
    question_id: str
    rubric_id: Optional[str] = None
    subject: str = "General"
    image_url: str
    raw_ocr_text: Optional[str] = None
    corrected_text: Optional[str] = None
    status: str = "uploaded"  # uploaded -> ocr_completed -> evaluated -> approved
    created_at: str
    created_by: str = "faculty"

# ----------------- OCR Schemas -----------------
class OCRResponse(BaseModel):
    sheet_id: str
    raw_text: str
    confidence: float
    status: str = "ocr_completed"

class OCRPatchRequest(BaseModel):
    corrected_text: str

class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None

# ----------------- LLM Evaluation Schemas -----------------
class MatchedPoint(BaseModel):
    rubric_item_id: str
    point_text: str
    marks_awarded: float
    evidence: str

class MissingPoint(BaseModel):
    rubric_item_id: str
    point_text: str
    marks_deducted: float
    reason: str

class EvaluationResponse(BaseModel):
    suggested_marks: float
    max_marks: float
    matched_points: List[MatchedPoint]
    missing_points: List[MissingPoint]
    feedback: str
    confidence: float

class EvaluateRequest(BaseModel):
    rubric_id: str

# ----------------- Score Schemas -----------------
class ApproveScoreRequest(BaseModel):
    final_marks: float
    edited_flag: bool = False
    override_reason: Optional[str] = None

class Score(BaseModel):
    sheet_id: str
    roll_no: str
    question_id: str
    rubric_id: str
    suggested_marks: float
    max_marks: float
    matched_points: List[MatchedPoint]
    missing_points: List[MissingPoint]
    feedback: str
    confidence: float
    final_marks: float
    edited_flag: bool
    override_reason: Optional[str] = None
    approved_by: str
    approved_at: str

class ResultSummaryItem(BaseModel):
    sheet_id: str
    roll_no: str
    question_id: str
    rubric_id: str
    final_marks: float
    max_marks: float
    suggested_marks: float
    edited_flag: bool
    confidence: float
    approved_at: str
    status: str
