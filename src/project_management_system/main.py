from fastapi.openapi.docs import get_swagger_ui_html
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from contextlib import asynccontextmanager
from project_management_system.routers import auth, projects, boards, board_columns, tasks
from project_management_system.deps import get_current_user, db_dependency
from project_management_system.database import Base, engine, get_db, SessionLocal
from project_management_system.seed import seed_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

app = FastAPI(
    title="Project Management System",
    description="A simple project management system built with FastAPI and uvicorn using uv package manager.", 
    version="1.0.0",
    lifespan=lifespan
    )

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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