from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, get_current_user
from app.db.models import User
from app.db.session import get_db
from app.core.limiter import limiter
from app.schemas.auth import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    EmailAlreadyExistsError,
    InvalidCurrentPasswordError,
    authenticate_user,
    change_user_password,
    create_user,
    delete_user_account,
    update_user_profile,
)
from app.services.password_reset_service import InvalidPasswordResetTokenError, request_password_reset, reset_password_with_token
from app.services.email_verification_service import InvalidEmailVerificationTokenError, send_email_verification, verify_email_with_token


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_user(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    try:
        user = create_user(db, payload)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc
    send_email_verification(db, user)
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


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    request_password_reset(db, str(payload.email))
    return MessageResponse(message="If the email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    try:
        reset_password_with_token(db, payload.token, payload.new_password)
    except InvalidPasswordResetTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired password reset token") from exc
    return MessageResponse(message="Password has been reset successfully")


@router.delete("/me", response_model=MessageResponse)
@limiter.limit("5/minute")
def delete_current_user(
    request: Request,
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        delete_user_account(db, current_user, payload)
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect") from exc
    return MessageResponse(message="Account deleted successfully")


@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit("5/minute")
def verify_email(request: Request, payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> MessageResponse:
    try:
        verify_email_with_token(db, payload.token)
    except InvalidEmailVerificationTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired email verification token") from exc
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("3/minute")
def resend_verification(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MessageResponse:
    send_email_verification(db, current_user)
    return MessageResponse(message="Verification email sent successfully")
