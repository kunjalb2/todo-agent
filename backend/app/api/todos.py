"""Todos API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    create_todo,
    delete_todo,
    get_todo,
    get_todos,
    toggle_todo_complete,
    update_todo,
)
from app.database import get_db
from app.dependencies import CurrentUserDep, DbDep
from app.models.todo import Priority
from app.schemas.todo import (
    TodoCreate,
    TodoResponse,
    TodoUpdate,
    PaginatedTodoResponse,
)

router = APIRouter(prefix="/todos", tags=["Todos"])


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo_endpoint(
    todo_data: TodoCreate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> TodoResponse:
    """Create a new todo."""
    todo = await create_todo(
        db,
        user_id=current_user.id,
        title=todo_data.title,
        description=todo_data.description,
        due_date=todo_data.due_date,
        priority=todo_data.priority,
    )
    return TodoResponse.model_validate(todo)


@router.get("", response_model=PaginatedTodoResponse)
async def get_todos_endpoint(
    current_user: CurrentUserDep,
    db: DbDep,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of records to return"),
    date_from: Optional[datetime] = Query(None, description="Filter todos from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter todos until this date"),
    completed_only: Optional[bool] = Query(None, description="Filter by completion status"),
) -> PaginatedTodoResponse:
    """Get all todos for the current user with optional filtering."""
    todos, total = await get_todos(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        completed_only=completed_only,
    )
    return PaginatedTodoResponse(
        items=[TodoResponse.model_validate(todo) for todo in todos],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
    )


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo_endpoint(
    todo_id: int,
    current_user: CurrentUserDep,
    db: DbDep,
) -> TodoResponse:
    """Get a single todo by ID."""
    todo = await get_todo(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return TodoResponse.model_validate(todo)


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo_endpoint(
    todo_id: int,
    todo_data: TodoUpdate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> TodoResponse:
    """Update a todo."""
    todo = await update_todo(
        db,
        todo_id=todo_id,
        user_id=current_user.id,
        title=todo_data.title,
        description=todo_data.description,
        due_date=todo_data.due_date,
        priority=todo_data.priority,
        is_completed=todo_data.is_completed,
    )
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return TodoResponse.model_validate(todo)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo_endpoint(
    todo_id: int,
    current_user: CurrentUserDep,
    db: DbDep,
) -> None:
    """Delete a todo."""
    success = await delete_todo(db, todo_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )


@router.patch("/{todo_id}/complete", response_model=TodoResponse)
async def toggle_todo_complete_endpoint(
    todo_id: int,
    current_user: CurrentUserDep,
    db: DbDep,
) -> TodoResponse:
    """Toggle the completion status of a todo."""
    todo = await toggle_todo_complete(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return TodoResponse.model_validate(todo)
