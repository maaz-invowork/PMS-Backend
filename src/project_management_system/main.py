from fastapi.openapi.docs import get_swagger_ui_html
from fastapi import FastAPI, status
from typing import Annotated
from routers import auth, projects, boards, board_columns, tasks
from deps import get_current_user
from database import Base, engine, get_db, SessionLocal
from deps import db_dependency

app = FastAPI(
    title="Project Management System",
    description="A simple project management system built with FastAPI and uvicorn using uv package manager.", 
    version="1.0.0",
    )

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(boards.router)
app.include_router(board_columns.router)
app.include_router(tasks.router)

Base.metadata.create_all(bind=engine)

@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {"message": "Project Management System is running!"}

@app.get("/health")
def health_check(db: db_dependency):
    return {"status": "online", "database": "connected"}