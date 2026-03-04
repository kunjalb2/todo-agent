"""Todo schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from enum import Enum


class Priority(str, Enum):
    """Priority levels for todos."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TodoBase(BaseModel):
    """Base todo schema."""

    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM


class TodoCreate(TodoBase):
    """Todo creation schema."""

    pass


class TodoUpdate(BaseModel):
    """Todo update schema."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[Priority] = None
    is_completed: Optional[bool] = None


class TodoResponse(TodoBase):
    """Todo response schema."""

    id: int
    user_id: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedTodoResponse(BaseModel):
    """Paginated todo response schema."""

    items: list[TodoResponse]
    total: int
    page: int = 1
    page_size: int = 10
