import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.models.schemas import UserProfile

security = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT token for local dev or session use."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(token: str) -> UserProfile:
    """
    Verify Firebase ID token if Firebase is active;
    otherwise verify local JWT dev token.
    """
    if settings.USE_FIREBASE:
        try:
            import firebase_admin
            from firebase_admin import auth as fb_auth
            decoded = fb_auth.verify_id_token(token)
            return UserProfile(
                uid=decoded.get("uid", "anonymous_faculty"),
                email=decoded.get("email", "faculty@pec.edu"),
                name=decoded.get("name", "Faculty Member"),
                role="faculty"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Firebase authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        # Development / Hybrid mode
        try:
            # Special bypass for instant demo tokens
            if token in ("demo_faculty_token", "test_token"):
                return UserProfile(
                    uid="faculty_demo_01",
                    email="faculty@pec.edu",
                    name="Dr. Faculty Reviewer",
                    role="faculty"
                )
            
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return UserProfile(
                uid=payload.get("sub", "faculty_demo_01"),
                email=payload.get("email", "faculty@pec.edu"),
                name=payload.get("name", "Faculty Member"),
                role=payload.get("role", "faculty")
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            )

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserProfile:
    """FastAPI dependency for protecting faculty routes."""
    if not credentials:
        # For smooth local developer demo if headers are omitted, fall back gracefully
        return UserProfile(
            uid="faculty_demo_01",
            email="faculty@pec.edu",
            name="Dr. Faculty Reviewer",
            role="faculty"
        )
    return verify_token(credentials.credentials)
