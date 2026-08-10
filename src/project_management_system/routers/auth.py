import os
from datetime import datetime, timedelta, timezone
from typing import Annotated
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import select
from dotenv import load_dotenv
import schemas
from deps import db_dependency, user_dependency
from models import User, Role

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )

def authenticate_user(username: str, password: str, db: Session):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {"sub": username, "id": user_id}
    expire = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expire})
    encoded_jwt = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
async def create_user(
    create_user_request: schemas.UserCreate, db: db_dependency
):

    existing_user_stmt = select(User).where(
        (User.username == create_user_request.username) | 
        (User.email == create_user_request.email)
    )
    if db.scalar(existing_user_stmt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered.",
        )

    role_stmt = select(Role).where(Role.name == "member")
    default_role = db.scalar(role_stmt)

    if not default_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default 'member' role not found in database.",
        )

    created_user = User(
        username=create_user_request.username,
        email=create_user_request.email,
        full_name=create_user_request.full_name,
        hashed_password=hash_password(create_user_request.password),
        role_id=default_role.id
    )

    db.add(created_user)
    db.commit()
    db.refresh(created_user)

    return created_user

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:    
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Couldn't validate user.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.username, user.id, timedelta(minutes=20))
    return {"access_token": token, "token_type": "bearer"}

@router.get("/user", status_code=status.HTTP_200_OK, response_model=schemas.UserResponse)
async def get_user_profile(current_user: user_dependency):
    return current_user