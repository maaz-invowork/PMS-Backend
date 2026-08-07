from fastapi import FastAPI, status, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from . import auth
from .auth import get_current_user
from .database import Base, engine, get_db
from . import models
from .database import engine, SessionLocal

app = FastAPI(title="Project Management System", description="A simple project management system built with FastAPI and uvicorn using uv package manager.", version="1.0.0")
app.include_router(auth.router)

Base.metadata.create_all(bind=engine)

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {"message": "Project Management System is running!"}

@app.get("/health")
def health_check(db: db_dependency):
    return {"status": "online", "database": "connected"}

@app.get("/user", status_code=status.HTTP_200_OK)
async def user(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication Failed.",
        )
    return {"user": user}