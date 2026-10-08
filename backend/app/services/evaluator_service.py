import json
import re
from typing import Dict, Any, List, Optional
from app.config import settings
from app.models.schemas import EvaluationResponse, MatchedPoint, MissingPoint, Rubric

class EvaluatorService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._genai_client = None
        if self.api_key:
            self._init_gemini()

    def _init_gemini(self):
        try:
            from google import genai
            self._genai_client = genai.Client(api_key=self.api_key)
            print(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            print(f"Warning: Could not initialize Google GenAI client: {e}")
            self._genai_client = None

    def build_prompt(self, rubric: Dict[str, Any], student_answer: str) -> str:
        rubric_points_str = "\n".join([
            f"- [ID: {p['id']}] ({p['marks']} marks): {p['text']}"
            for p in rubric.get("rubric_points", [])
        ])

        prompt = f"""You are an objective, rigorous academic evaluator grading a handwritten student answer for a university examination.
Grade strictly according to the checklist rubric provided below.

QUESTION:
{rubric.get("question_text", "")}

REFERENCE / MODEL ANSWER:
{rubric.get("model_answer", "")}

MAXIMUM MARKS:
{rubric.get("max_marks", 0)}

POINT-WISE RUBRIC CHECKLIST:
{rubric_points_str}

STUDENT'S EXTRACTED ANSWER (from OCR):
"{student_answer}"

GRADING INSTRUCTIONS:
1. Examine each rubric point independently.
2. If the student answer demonstrates understanding or includes the required criterion, mark it as MATCHED. Award the points and cite the exact quote/evidence from the student's text.
3. If the criterion is absent, incorrect, or incomplete, mark it as MISSING. Specify marks deducted and explain the missing element clearly.
4. Sum up marks awarded to calculate 'suggested_marks'. Do not exceed maximum marks.
5. Provide a constructive 2-3 sentence feedback summary for the student.
6. Self-report a confidence score between 0.00 and 1.00 regarding your grading certainty.

OUTPUT REQUIREMENT:
You must respond with valid JSON matching this schema:
{{
  "suggested_marks": float,
  "max_marks": float,
  "matched_points": [
    {{
      "rubric_item_id": "string",
      "point_text": "string",
      "marks_awarded": float,
      "evidence": "exact quote or evidence from student answer"
    }}
  ],
  "missing_points": [
    {{
      "rubric_item_id": "string",
      "point_text": "string",
      "marks_deducted": float,
      "reason": "why this point was deducted or what was missing"
    }}
  ],
  "feedback": "2-3 sentences of constructive feedback",
  "confidence": float
}}
"""
        return prompt

    def evaluate_with_gemini(self, rubric: Dict[str, Any], student_answer: str) -> EvaluationResponse:
        """Call Gemini API with temperature 0 and structured JSON output."""
        from google.genai import types

        prompt = self.build_prompt(rubric, student_answer)

        try:
            response = self._genai_client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text.strip()
            # Clean markdown formatting if present
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                raw_text = re.sub(r"\n?```$", "", raw_text)
            
            data = json.loads(raw_text)
            return EvaluationResponse(**data)
        except Exception as e:
            print(f"Gemini API call failed: {e}. Switching to heuristic rubric evaluator.")
            return self.heuristic_evaluate(rubric, student_answer)

    def heuristic_evaluate(self, rubric: Dict[str, Any], student_answer: str) -> EvaluationResponse:
        """
        Deterministic, rule-based rubric evaluation fallback.
        Ensures consistent behavior and zero downtime even before an API key is supplied.
        """
        rubric_points = rubric.get("rubric_points", [])
        max_marks = float(rubric.get("max_marks", sum(p.get("marks", 0) for p in rubric_points)))
        
        matched: List[MatchedPoint] = []
        missing: List[MissingPoint] = []
        awarded_total = 0.0
        
        student_lower = student_answer.lower()
        
        for p in rubric_points:
            p_id = p.get("id", "pt")
            p_text = p.get("text", "")
            p_marks = float(p.get("marks", 1.0))
            
            # Extract keywords from the rubric text
            words = [w.strip(".,;:()[]\"'") for w in p_text.lower().split() if len(w) > 3]
            match_count = sum(1 for w in words if w in student_lower)
            is_matched = (match_count >= max(1, len(words) // 2)) or (len(words) == 0 and len(student_lower) > 20)
            
            if is_matched:
                matched.append(MatchedPoint(
                    rubric_item_id=p_id,
                    point_text=p_text,
                    marks_awarded=p_marks,
                    evidence=f"Identified alignment in answer concerning key concepts ({', '.join(words[:2]) if words else 'content'})."
                ))
                awarded_total += p_marks
            else:
                missing.append(MissingPoint(
                    rubric_item_id=p_id,
                    point_text=p_text,
                    marks_deducted=p_marks,
                    reason=f"Criterion '{p_text}' was not sufficiently articulated in the answer."
                ))

        suggested_marks = min(awarded_total, max_marks)
        confidence = 0.92 if matched else 0.75
        
        feedback = (
            f"The student correctly addressed {len(matched)} of {len(rubric_points)} key rubric criteria. "
            f"Key strengths include foundational conceptual definitions. "
            f"To achieve full marks, additional detail was required for {len(missing)} missing point(s)."
        )

        return EvaluationResponse(
            suggested_marks=round(suggested_marks, 2),
            max_marks=round(max_marks, 2),
            matched_points=matched,
            missing_points=missing,
            feedback=feedback,
            confidence=confidence
        )

    def evaluate(self, rubric: Dict[str, Any], student_answer: str) -> EvaluationResponse:
        """Entry point for rubric-conditioned grading."""
        if self._genai_client is None and settings.GEMINI_API_KEY:
            self.api_key = settings.GEMINI_API_KEY
            self._init_gemini()

        if self._genai_client is not None:
            return self.evaluate_with_gemini(rubric, student_answer)
        else:
            return self.heuristic_evaluate(rubric, student_answer)

evaluator_service = EvaluatorService()
