from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import db_dependency
from deps import require_permission
from models import Board, Project, User
import schemas

router = APIRouter(prefix="/boards", tags=["Boards"])


def check_project_access(project: Project, current_user: User):
    is_admin = current_user.role.name == "admin"
    is_member_or_owner = (
        project.owner_id == current_user.id or 
        any(m.id == current_user.id for m in project.members)
    )
    if not (is_admin or is_member_or_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access.",
        )

@router.post("/", response_model=schemas.BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(
    board_data: schemas.BoardCreate,
    db: db_dependency,
    current_user: User = Depends(require_permission("board:manage")),
):
    stmt = select(Project).where(Project.id == board_data.project_id)
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    is_admin = current_user.role.name == "admin"
    is_owner = project.owner_id == current_user.id

    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner or an admin can create boards for this project.",
        )

    new_board = Board(
        name=board_data.name,
        description=board_data.description,
        project_id=board_data.project_id,
    )
    db.add(new_board)
    db.commit()
    db.refresh(new_board)

    return new_board


@router.get("/project/{project_id}", response_model=List[schemas.BoardResponse])
async def list_project_boards(
    project_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:read")),
):
    # Verify project exists and user has access
    project_stmt = select(Project).options(selectinload(Project.members)).where(Project.id == project_id)
    project = db.scalar(project_stmt)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    check_project_access(project, current_user)

    stmt = select(Board).where(Board.project_id == project_id)
    return db.scalars(stmt).all()



@router.get("/{board_id}", response_model=schemas.BoardResponse)
async def get_board(
    board_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:read")),
):
    stmt = (
        select(Board)
        .options(selectinload(Board.project).selectinload(Project.members))
        .where(Board.id == board_id)
    )
    board = db.scalar(stmt)

    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found.",
        )

    check_project_access(board.project, current_user)
    return board


@router.patch("/{board_id}", response_model=schemas.BoardResponse)
async def update_board(
    board_id: int,
    board_update: schemas.BoardUpdate,
    db: db_dependency,
    current_user: User = Depends(require_permission("board:manage")),
):
    stmt = (
        select(Board)
        .options(selectinload(Board.project).selectinload(Project.members))
        .where(Board.id == board_id)
    )
    board = db.scalar(stmt)

    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found.",
        )

    is_admin = current_user.role.name == "admin"
    is_owner = project.owner_id == current_user.id

    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner or an admin can create boards for this project.",
        )

    update_data = board_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(board, field, value)

    db.commit()
    db.refresh(board)
    return board


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("board:manage")),
):
    stmt = (
        select(Board)
        .options(selectinload(Board.project).selectinload(Project.members))
        .where(Board.id == board_id)
    )
    board = db.scalar(stmt)

    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found.",
        )

    check_project_access(board.project, current_user)

    db.delete(board)
    db.commit()
    return None