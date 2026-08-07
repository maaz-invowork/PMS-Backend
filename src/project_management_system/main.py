from fastapi import FastAPI, status, Depends, HTTPException
from typing import Annotated
from sqlalchemy import text
from sqlalchemy.orm import Session
import auth
from models import User
from deps import get_current_user
from database import Base, engine, get_db, SessionLocal
from deps import db_dependency, user_dependency
import schemas

app = FastAPI(title="Project Management System", description="A simple project management system built with FastAPI and uvicorn using uv package manager.", version="1.0.0")

app.include_router(auth.router)
Base.metadata.create_all(bind=engine)

@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {"message": "Project Management System is running!"}

@app.get("/health")
def health_check(db: db_dependency):
    return {"status": "online", "database": "connected"}

@app.get("/user", status_code=status.HTTP_200_OK, response_model=schemas.UserResponse)
async def get_user_profile(current_user: user_dependency, db: db_dependency):
    return current_user