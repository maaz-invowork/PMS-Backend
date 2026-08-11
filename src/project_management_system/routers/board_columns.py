from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from deps import require_permission, db_dependency, check_access
from models import BoardColumn, Board, Project, User
import schemas

router = APIRouter(prefix="/board-columns", tags=["Board Columns"])


@router.post("/", response_model=schemas.BoardColumnResponse, status_code=status.HTTP_201_CREATED)
async def create_board_column(
    column_data: schemas.BoardColumnCreate,
    db: db_dependency,
    current_user: User = Depends(require_permission("column:manage")),
):
    stmt = (
    select(Board)
    .options(selectinload(Board.project))
    .where(Board.id == column_data.board_id)
    )
    board = db.scalar(stmt)

    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found.",
        )
    
    is_admin = current_user.role.name == "admin"
    is_owner = board.project.owner_id == current_user.id

    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner or an admin can add Board Column.",
        )

    # Auto-calculate position if left as default 0
    position = column_data.position
    if position == 0:
        max_pos_stmt = select(func.coalesce(func.max(BoardColumn.position), 0)).where(
            BoardColumn.board_id == column_data.board_id
        )
        position = db.scalar(max_pos_stmt) + 1

    new_column = BoardColumn(
        name=column_data.name,
        board_id=column_data.board_id,
        position=position,
    )
    db.add(new_column)
    db.commit()
    db.refresh(new_column)

    new_column.tasks = []
    return new_column


@router.get("/board/{board_id}", response_model=List[schemas.BoardColumnResponse])
async def list_board_columns(
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

    check_access(board.project, current_user)

    # Fetch columns ordered by position, eager-loading nested tasks
    cols_stmt = (
        select(BoardColumn)
        .options(selectinload(BoardColumn.tasks))
        .where(BoardColumn.board_id == board_id)
        .order_by(BoardColumn.position.asc())
    )
    return db.scalars(cols_stmt).all()


@router.get("/{column_id}", response_model=schemas.BoardColumnResponse)
async def get_board_column(
    column_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:read")),
):
    stmt = (
        select(BoardColumn)
        .options(
            selectinload(BoardColumn.tasks),
            selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members)
        )
        .where(BoardColumn.id == column_id)
    )
    column = db.scalar(stmt)

    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Column not found.",
        )

    check_access(column.board.project, current_user)
    return column

@router.patch("/{column_id}", response_model=schemas.BoardColumnResponse)
async def update_board_column(
    column_id: int,
    column_update: schemas.BoardColumnUpdate,
    db: db_dependency,
    current_user: User = Depends(require_permission("column:manage")),
):
    stmt = (
        select(BoardColumn)
        .options(
            selectinload(BoardColumn.tasks),
            selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members)
        )
        .where(BoardColumn.id == column_id)
    )
    column = db.scalar(stmt)

    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Column not found.",
        )

    is_admin = current_user.role.name == "admin"
    is_owner = column.board.project.owner_id == current_user.id

    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner or an admin can update Board Column.",
        )

    update_data = column_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(column, field, value)

    db.commit()
    db.refresh(column)
    return column

@router.delete("/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board_column(
    column_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("column:manage")),
):
    stmt = (
        select(BoardColumn)
        .options(
            selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members)
        )
        .where(BoardColumn.id == column_id)
    )
    column = db.scalar(stmt)

    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Column not found.",
        )

    is_admin = current_user.role.name == "admin"
    is_owner = column.board.project.owner_id == current_user.id

    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner or an admin can delete Board Column.",
        )

    db.delete(column)
    db.commit()
    return None