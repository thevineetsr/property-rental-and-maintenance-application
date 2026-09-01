from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.dependencies.auth import get_current_user
from backend.app.dependencies.permissions import require_manager, require_authenticated
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from backend.app.schemas.user import UserResponse
from backend.app.services.auth_service import (
    register_user,
    authenticate_user,
    get_all_contractors,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    return register_user(db, request)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Sign in with email and password to receive a JWT access token."""
    return authenticate_user(db, request)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(require_authenticated)):
    """Retrieve profile and role of currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get("/contractors", response_model=List[UserResponse])
def list_contractors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """List all registered maintenance contractors. Restricted to Property Managers."""
    contractors = get_all_contractors(db)
    return [UserResponse.model_validate(c) for c in contractors]
