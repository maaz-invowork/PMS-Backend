import enum
from sqlalchemy import Column, Integer, ForeignKey, String, Text, Table
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

# Association tables for many-to-many relationships
project_members = Table(
    "project_members",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "project_id",
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    users: Mapped[List["User"]] = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id : Mapped[int] = mapped_column(primary_key=True, index=True)
    username : Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email : Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name : Mapped[str] = mapped_column(String(100))
    hashed_password : Mapped[str] = mapped_column(String(255))
    role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="users")
    owned_projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="owner"
    )
    assigned_projects: Mapped[List["Project"]] = relationship(
        "Project", secondary=project_members, back_populates="members"
    )
    assigned_tasks: Mapped[List["Task"]] = relationship(
        "Task", foreign_keys="[Task.assignee_id]", back_populates="assignee"
    )
    created_tasks: Mapped[List["Task"]] = relationship(
        "Task", foreign_keys="[Task.created_by_id]", back_populates="creator"
    )

    @property
    def permission_names(self) -> set[str]:
        if not self.role or not self.role.permissions:
            return set()
        return {permission.name for permission in self.role.permissions}

    def has_permission(self, permission_name: str) -> bool:
        return permission_name in self.permission_names

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Relationships
    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_projects"
    )
    members: Mapped[List["User"]] = relationship(
        "User", secondary=project_members, back_populates="assigned_projects"
    )
    boards: Mapped[List["Board"]] = relationship(
        "Board", back_populates="project", cascade="all, delete-orphan"
    )


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="boards")
    columns: Mapped[List["BoardColumn"]] = relationship(
        "BoardColumn",
        back_populates="board",
        cascade="all, delete-orphan",
        order_by="BoardColumn.position",
    )


class BoardColumn(Base):
    __tablename__ = "board_columns"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(50)
    )
    position: Mapped[int] = mapped_column(
        default=0
    )
    board_id: Mapped[int] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE")
    )

    # Relationships
    board: Mapped["Board"] = relationship("Board", back_populates="columns")
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="column",
        cascade="all, delete-orphan",
        order_by="Task.position",
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(
        default=0
    )
    column_id: Mapped[int] = mapped_column(
        ForeignKey("board_columns.id", ondelete="CASCADE")
    )
    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    column: Mapped["BoardColumn"] = relationship(
        "BoardColumn", back_populates="tasks"
    )
    assignee: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assignee_id], back_populates="assigned_tasks"
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by_id], back_populates="created_tasks"
    )