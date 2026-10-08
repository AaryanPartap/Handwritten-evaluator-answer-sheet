from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import TokenVerifyRequest, UserProfile
from app.auth.security import verify_token, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/verify", response_model=UserProfile)
def verify_auth_token(req: TokenVerifyRequest):
    """
    Verifies Firebase ID token or dev token and returns user profile.
    """
    return verify_token(req.token)

@router.post("/login", response_model=dict)
def dev_login(credentials: dict):
    """
    Faculty login endpoint for development / local mode.
    Returns access_token and user profile.
    """
    email = credentials.get("email", "faculty@pec.edu")
    token = create_access_token({"sub": "faculty_01", "email": email, "role": "faculty", "name": "Faculty Reviewer"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "uid": "faculty_01",
            "email": email,
            "name": "Faculty Reviewer",
            "role": "faculty"
        }
    }
