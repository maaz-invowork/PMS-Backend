from typing import Annotated, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from project_management_system.config import settings
from project_management_system.database import  SessionLocal, get_db
from project_management_system.models import User, Role

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

db_dependency = Annotated[Session, Depends(get_db)]

async def get_current_user(
    token: Annotated[str, Depends(oauth2_bearer)],
    db: db_dependency,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = (
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    user = db.scalar(stmt)

    if user is None:
        raise credentials_exception

    return user

user_dependency = Annotated[User, Depends(get_current_user)]


def require_permission(permission_name: str) -> Callable:
    def permission_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not current_user.has_permission(permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' is required to perform this action.",
            )
        return current_user

    return permission_checker

def check_access(project: Project, current_user: User, mesg: str = "You do not have access to this project."):
    is_admin = current_user.role.name == "admin"
    is_member_or_owner = (
        project.owner_id == current_user.id or
        any(m.id == current_user.id for m in project.members)
    )
    if not (is_admin or is_member_or_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=mesg,
        )

