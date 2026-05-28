from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, get_current_user
from app.db.models import User
from app.db.session import get_db
from app.core.limiter import limiter
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse, UpdateProfileRequest, UserResponse
from app.services.auth_service import (
    EmailAlreadyExistsError,
    InvalidCurrentPasswordError,
    authenticate_user,
    change_user_password,
    create_user,
    update_user_profile,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_user(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    try:
        user = create_user(db, payload)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login_user(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        token_type="bearer",
        expires_in_minutes=settings.access_token_expire_minutes,
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
@limiter.limit("5/minute")
def update_current_user(
    request: Request,
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        user = update_user_profile(db, current_user, payload)
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect") from exc
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc
    return UserResponse.model_validate(user)


@router.post("/change-password", response_model=UserResponse)
@limiter.limit("5/minute")
def change_current_user_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        user = change_user_password(db, current_user, payload)
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect") from exc
    return UserResponse.model_validate(user)
