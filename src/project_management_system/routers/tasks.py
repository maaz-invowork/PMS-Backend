from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from project_management_system.redis_client import invalidate_board_cache

from project_management_system.deps import require_permission, db_dependency, check_access
from project_management_system.models import Task, BoardColumn, Board, Project, User
import project_management_system.schemas as schemas

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def verify_assignee(assignee_id: Optional[int], project: Project):
    if assignee_id is None:
        return

    is_owner = project.owner_id == assignee_id
    is_member = any(m.id == assignee_id for m in project.members)

    if not (is_owner or is_member):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned user must be a member or owner of the project.",
        )

@router.post("/", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: schemas.TaskCreate,
    db: db_dependency,
    current_user: User = Depends(require_permission("task:create")),
):
    # Fetch target column with parent Board and Project details
    col_stmt = (
        select(BoardColumn)
        .options(
            selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members)
        )
        .where(BoardColumn.id == task_data.column_id)
    )
    column = db.scalar(col_stmt)

    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board column not found.",
        )

    project = column.board.project
    check_access(project, current_user)

    # Validate assignee belongs to the project
    if task_data.assignee_id:
        verify_assignee(task_data.assignee_id, project)

    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
        column_id=task_data.column_id,
        assignee_id=task_data.assignee_id,
        created_by_id=current_user.id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task, ['assignee', 'creator'])

    await invalidate_board_cache(column.board_id)
    
    return new_task

@router.get("/column/{column_id}", response_model=List[schemas.TaskResponse])
async def list_column_tasks(
    column_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:read")),
):
    col_stmt = (
        select(BoardColumn)
        .options(
            selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members)
        )
        .where(BoardColumn.id == column_id)
    )
    column = db.scalar(col_stmt)

    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board column not found.",
        )

    check_access(column.board.project, current_user)

    tasks_stmt = (
        select(Task)
        .options(selectinload(Task.assignee),
                selectinload(Task.creator))
        .where(Task.column_id == column_id)
        .order_by(Task.position.asc())
    )
    return db.scalars(tasks_stmt).all()

@router.get("/{task_id}", response_model=schemas.TaskResponse)
async def get_task(
    task_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:read")),
):
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.column)
            .selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members),
        )
        .where(Task.id == task_id)
    )
    task = db.scalar(stmt)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    check_access(task.column.board.project, current_user)
    return task

@router.patch("/{task_id}", response_model=schemas.TaskResponse)
async def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: db_dependency,
    current_user: User = Depends(require_permission("task:update")),
):
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.column)
            .selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members),
        )
        .where(Task.id == task_id)
    )
    task = db.scalar(stmt)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    project = task.column.board.project
    check_access(project, current_user)

    update_data = task_update.model_dump(exclude_unset=True)

    if "assignee_id" in update_data and update_data["assignee_id"] is not None:
        verify_assignee(update_data["assignee_id"], project)

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task, ['assignee', 'creator'])
    
    await invalidate_board_cache(task.column.board_id)
    
    return task

@router.patch("/{task_id}/status", response_model=schemas.TaskResponse)
async def update_task_status(
    task_id: int,
    move_data: schemas.TaskMove,
    db: db_dependency,
    current_user: User = Depends(require_permission("task:status_update")),
):
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.column)
            .selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members),
        )
        .where(Task.id == task_id)
    )
    task = db.scalar(stmt)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    check_access(task.column.board.project, current_user)

    # Verify target column exists
    target_col_stmt = select(BoardColumn).where(BoardColumn.id == move_data.column_id)
    target_column = db.scalar(target_col_stmt)

    if not target_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination column not found.",
        )

    task.column_id = move_data.column_id
    task.position = move_data.position
    db.commit()
    db.refresh(task, ["assignee", "creator"])

    await invalidate_board_cache(task.column.board_id)

    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("task:delete")),
):
    stmt = (
        select(Task)
        .options(
            selectinload(Task.column)
            .selectinload(BoardColumn.board)
            .selectinload(Board.project)
            .selectinload(Project.members)
        )
        .where(Task.id == task_id)
    )
    task = db.scalar(stmt)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    check_access(task.column.board.project, current_user)

    db.delete(task)
    db.commit()

    await invalidate_board_cache(task.column.board_id)
    
    return None