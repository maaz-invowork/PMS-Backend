from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from deps import require_permission

from deps import db_dependency, user_dependency
from models import Project, User
import schemas

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ProjectResponse)
async def create_project(
    project_data: schemas.ProjectCreate,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:create")),
):
    new_project = Project(
        title=project_data.title,
        description=project_data.description,
        owner_id=current_user.id,
    )

    db.add(new_project)
    db.commit()

    # Re-query with eager loading to populate relationship models for ProjectResponse
    stmt = (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.members),
            selectinload(Project.boards),
        )
        .where(Project.id == new_project.id)
    )
    return db.scalar(stmt)

@router.get("/", response_model=List[schemas.ProjectResponse])
async def list_user_projects(
    db: db_dependency,
    current_user: User = Depends(require_permission("project:read"))
):
    stmt = (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.members),
            selectinload(Project.boards),
        )
    )

    if current_user.role.name != "admin":
        stmt = stmt.where(
            or_(
                Project.owner_id == current_user.id,
                Project.members.any(User.id == current_user.id),
            )
        )

    return db.scalars(stmt.distinct()).all()

@router.get("/{project_id}", response_model=schemas.ProjectResponse)
async def get_project(
    project_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:read"))
):
    stmt = (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.members),
            selectinload(Project.boards),
        )
        .where(Project.id == project_id)
    )
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    is_admin = current_user.role.name == "admin"

    is_member_or_owner = (
        project.owner_id == current_user.id or 
        any(m.id == current_user.id for m in project.members)
    )

    if not (is_admin or is_member_or_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project.",
        )

    return project

@router.patch("/{project_id}", response_model=schemas.ProjectResponse)
async def update_project(
    project_id: int,
    project_update: schemas.ProjectUpdate,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:update")),
):
    stmt = (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.members),
            selectinload(Project.boards),
        )
        .where(Project.id == project_id)
    )
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    is_admin = current_user.role.name == "admin"

    if not is_admin and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and project owner can update project details.",
        )

    update_data = project_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: db_dependency,
    current_user: User = Depends(require_permission("project:delete")),
):
    stmt = select(Project).where(Project.id == project_id)
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    is_admin = current_user.role.name == "admin"

    if not is_admin and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and project owner can delete project.",
        )

    db.delete(project)
    db.commit()
    return None

@router.post("/{project_id}/members", response_model=List[schemas.UserMinimalResponse])
async def add_project_members(
    project_id: int,
    member_data: schemas.ProjectMembersUpdate,
    db: db_dependency,
    current_user: User = Depends(require_permission("members:manage")),
):
    stmt = (
        select(Project)
        .options(
            selectinload(Project.members),
        )
        .where(Project.id == project_id)
    )
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found."
        )

    is_admin = current_user.role.name == "admin"
    if not is_admin and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin / project owners can add members.",
        )

    existing_ids = {m.id for m in project.members}
    new_users = [u for u in requested_users if u.id not in existing_ids]

    for user in new_users:
        project.members.append(user)

    db.commit()
    db.refresh(project, ["members"])
    
    return project.members

@router.post("/{project_id}/members/remove", response_model=List[schemas.UserMinimalResponse])
async def remove_project_members(
    project_id: int,
    member_data: schemas.ProjectMembersUpdate,
    db: db_dependency,
    current_user: User = Depends(require_permission("members:manage")),
):
    stmt = (
        select(Project)
        .options(
            selectinload(Project.members),
        )
        .where(Project.id == project_id)
    )
    project = db.scalar(stmt)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found."
        )

    is_admin = current_user.role.name == "admin"
    if not is_admin and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin / project owners can remove members.",
        )

    remove_ids = set(member_data.user_ids)
    project.members = [m for m in project.members if m.id not in remove_ids]

    db.commit()
    db.refresh(project, ["members"])

    return project.members