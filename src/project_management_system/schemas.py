from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class PermissionBase(BaseModel):
    name: str = Field(..., description="Unique permission key, e.g. 'project:create'")
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    name: str = Field(..., description="Role name, e.g. 'admin', 'member'")
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[int] = []


class RoleResponse(RoleBase):
    id: int
    permissions: List[PermissionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Raw password to be hashed")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    id: int
    role: Optional[RoleResponse] = None

    model_config = ConfigDict(from_attributes=True)

class UserMinimalResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    id: Optional[int] = None
    username: Optional[str] = None

class TaskBase(BaseModel):
    title: str = Field(..., max_length=100)
    description: Optional[str] = None
    priority: Optional[str] = Field("medium", description="e.g. low, medium, high, urgent")
    due_date: Optional[datetime] = None
    position: int = Field(default=0, description="Order position in column")


class TaskCreate(TaskBase):
    column_id: int
    assignee_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    position: Optional[int] = None
    column_id: Optional[int] = None
    assignee_id: Optional[int] = None


# Lightweight schema for reordering/moving tasks between columns
class TaskMove(BaseModel):
    column_id: int
    position: int


class TaskResponse(TaskBase):
    id: int
    column_id: int
    assignee: Optional[UserMinimalResponse] = None
    creator: Optional[UserMinimalResponse] = None

    model_config = ConfigDict(from_attributes=True)

class BoardColumnBase(BaseModel):
    name: str = Field(..., max_length=50)
    position: int = Field(default=0, description="Column order on board")

class BoardColumnCreate(BoardColumnBase):
    board_id: int

class BoardColumnUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    position: Optional[int] = None

class BoardColumnResponse(BoardColumnBase):
    id: int
    board_id: int
    tasks: List[TaskResponse] = []

    model_config = ConfigDict(from_attributes=True)


class BoardBase(BaseModel):
    name: str = Field(..., max_length=100)

class BoardCreate(BoardBase):
    project_id: int

class BoardUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)

class BoardResponse(BoardBase):
    id: int
    project_id: int
    columns: List[BoardColumnResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    title: str = Field(..., max_length=100)
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass  # Owner is set automatically from current_user

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None

class ProjectMembersUpdate(BaseModel):
    user_ids: List[int] = Field(..., min_length=1, description="List of user IDs to add")

class ProjectListResponse(ProjectBase):
    id: int
    owner: UserMinimalResponse
    members: List[UserMinimalResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ProjectDetailResponse(ProjectBase):
    id: int
    owner: UserMinimalResponse
    members: List[UserMinimalResponse] = []
    boards: List[BoardResponse] = []

    model_config = ConfigDict(from_attributes=True)




