from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.user import User, UserRole
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from backend.app.schemas.user import UserResponse


def register_user(db: Session, request: RegisterRequest) -> UserResponse:
    """Register a new user account."""
    existing = db.query(User).filter(User.email == request.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )
    
    new_user = User(
        email=request.email.lower(),
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role=request.role.value
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)


def authenticate_user(db: Session, request: LoginRequest) -> TokenResponse:
    """Authenticate user with email and password, returning a JWT token."""
    user = db.query(User).filter(User.email == request.email.lower()).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role
    }
    access_token = create_access_token(data=token_data)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


def get_all_contractors(db: Session) -> List[User]:
    """Retrieve all users with the MAINTENANCE_CONTRACTOR role."""
    return db.query(User).filter(
        User.role == UserRole.MAINTENANCE_CONTRACTOR.value
    ).order_by(User.full_name.asc()).all()
