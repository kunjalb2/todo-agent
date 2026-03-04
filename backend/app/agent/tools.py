"""Agent tools for todo management."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.todo import Todo, Priority


async def get_db_session() -> AsyncSession:
    """Get a database session for tool use."""
    async with async_session_maker() as session:
        yield session


async def get_todos(user_id: int, completed_only: Optional[bool] = None) -> dict:
    """List all todos for a user.

    Args:
        user_id: The ID of the user
        completed_only: If True, only show completed todos. If False, only show incomplete todos.

    Returns:
        A dictionary with a list of todos and summary information
    """
    async with async_session_maker() as session:
        query = select(Todo).where(Todo.user_id == user_id)

        if completed_only is not None:
            query = query.where(Todo.is_completed == completed_only)

        query = query.order_by(Todo.created_at.desc())

        result = await session.execute(query)
        todos = result.scalars().all()

        todos_list = [
            {
                "id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "priority": todo.priority,
                "is_completed": todo.is_completed,
            }
            for todo in todos
        ]

        total = len(todos_list)
        completed = sum(1 for t in todos_list if t["is_completed"])

        return {
            "todos": todos_list,
            "total": total,
            "completed": completed,
            "pending": total - completed,
        }


async def create_todo(
    user_id: int,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: str = "medium",
) -> dict:
    """Create a new todo for a user.

    Args:
        user_id: The ID of the user
        title: The title of the todo
        description: Optional description of the todo
        due_date: Optional due date in ISO format
        priority: Priority level (low, medium, high)

    Returns:
        The created todo
    """
    async with async_session_maker() as session:
        due_date_obj = None
        if due_date:
            try:
                due_date_obj = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        todo = Todo(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date_obj,
            priority=Priority(priority),
        )
        session.add(todo)
        await session.commit()
        await session.refresh(todo)

        return {
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "due_date": todo.due_date.isoformat() if todo.due_date else None,
            "priority": todo.priority,
            "is_completed": todo.is_completed,
        }


async def update_todo(
    user_id: int,
    todo_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    is_completed: Optional[bool] = None,
) -> dict:
    """Update an existing todo.

    Args:
        user_id: The ID of the user
        todo_id: The ID of the todo to update
        title: New title for the todo
        description: New description for the todo
        due_date: New due date in ISO format
        priority: New priority level (low, medium, high)
        is_completed: New completion status

    Returns:
        The updated todo, or None if not found
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        )
        todo = result.scalar_one_or_none()

        if not todo:
            return None

        if title is not None:
            todo.title = title
        if description is not None:
            todo.description = description
        if due_date is not None:
            try:
                todo.due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except ValueError:
                pass
        if priority is not None:
            todo.priority = Priority(priority)
        if is_completed is not None:
            todo.is_completed = is_completed

        todo.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(todo)

        return {
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "due_date": todo.due_date.isoformat() if todo.due_date else None,
            "priority": todo.priority,
            "is_completed": todo.is_completed,
        }


async def delete_todo(user_id: int, todo_id: int) -> dict:
    """Delete a todo.

    Args:
        user_id: The ID of the user
        todo_id: The ID of the todo to delete

    Returns:
        Success status message
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        )
        todo = result.scalar_one_or_none()

        if not todo:
            return {"success": False, "message": "Todo not found"}

        await session.delete(todo)
        await session.commit()

        return {"success": True, "message": "Todo deleted successfully"}


async def complete_todo(user_id: int, todo_id: int) -> dict:
    """Mark a todo as complete.

    Args:
        user_id: The ID of the user
        todo_id: The ID of the todo to mark complete

    Returns:
        The updated todo, or None if not found
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        )
        todo = result.scalar_one_or_none()

        if not todo:
            return None

        todo.is_completed = True
        todo.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(todo)

        return {
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "due_date": todo.due_date.isoformat() if todo.due_date else None,
            "priority": todo.priority,
            "is_completed": todo.is_completed,
        }
