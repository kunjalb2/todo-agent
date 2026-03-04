"""CRUD operations for Todo model."""
from datetime import datetime
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.todo import Todo, Priority


async def create_todo(
    db: AsyncSession,
    user_id: int,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    priority: Priority = Priority.MEDIUM,
) -> Todo:
    """Create a new todo for a user."""
    todo = Todo(
        user_id=user_id,
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
    )
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


async def get_todo(db: AsyncSession, todo_id: int, user_id: int) -> Optional[Todo]:
    """Get a single todo by ID for a user."""
    result = await db.execute(
        select(Todo).where(and_(Todo.id == todo_id, Todo.user_id == user_id))
    )
    return result.scalar_one_or_none()


async def get_todos(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    completed_only: Optional[bool] = None,
) -> tuple[list[Todo], int]:
    """Get todos for a user with optional filtering."""
    # Build base query
    query = select(Todo).where(Todo.user_id == user_id)

    # Apply filters
    conditions = []
    if date_from:
        conditions.append(Todo.due_date >= date_from)
    if date_to:
        conditions.append(Todo.due_date <= date_to)
    if completed_only is not None:
        conditions.append(Todo.is_completed == completed_only)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(Todo.id)
    if conditions:
        count_query = count_query.where(and_(Todo.user_id == user_id, *conditions))
    else:
        count_query = count_query.where(Todo.user_id == user_id)

    count_result = await db.execute(count_query)
    total = len(count_result.all())

    # Apply pagination and ordering
    query = query.order_by(Todo.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    todos = list(result.scalars().all())

    return todos, total


async def update_todo(
    db: AsyncSession,
    todo_id: int,
    user_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    priority: Optional[Priority] = None,
    is_completed: Optional[bool] = None,
) -> Optional[Todo]:
    """Update a todo."""
    todo = await get_todo(db, todo_id, user_id)
    if not todo:
        return None

    if title is not None:
        todo.title = title
    if description is not None:
        todo.description = description
    if due_date is not None:
        todo.due_date = due_date
    if priority is not None:
        todo.priority = priority
    if is_completed is not None:
        todo.is_completed = is_completed

    todo.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(todo)
    return todo


async def delete_todo(db: AsyncSession, todo_id: int, user_id: int) -> bool:
    """Delete a todo."""
    todo = await get_todo(db, todo_id, user_id)
    if not todo:
        return False

    await db.delete(todo)
    await db.commit()
    return True


async def toggle_todo_complete(db: AsyncSession, todo_id: int, user_id: int) -> Optional[Todo]:
    """Toggle the completion status of a todo."""
    todo = await get_todo(db, todo_id, user_id)
    if not todo:
        return None

    todo.is_completed = not todo.is_completed
    todo.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(todo)
    return todo
