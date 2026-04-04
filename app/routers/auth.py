from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.models import User as UserModel
from app.schemas import UserCreate, User, Token, PasswordChange, PasswordResetRequest, PasswordResetConfirm
from app.auth import (
    authenticate_user,
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    generate_password_reset_token,
    verify_password_reset_token,
    consume_password_reset_token,
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user_by_username = db.query(UserModel).filter(UserModel.username == user.username).first()
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/reset-password-request")
def request_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    token = generate_password_reset_token(db, reset_request.email)
    if not token:
        return {"message": "If an account with that email exists, a reset link has been sent."}
    return {"message": "If an account with that email exists, a reset link has been sent.", "token": token}


@router.post("/reset-password")
def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    email = verify_password_reset_token(reset_confirm.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(reset_confirm.new_password)
    consume_password_reset_token(reset_confirm.token)
    db.commit()
    return {"message": "Password reset successfully"}
