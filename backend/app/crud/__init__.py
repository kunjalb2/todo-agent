"""CRUD operations."""
from app.crud.todo import (
    create_todo,
    get_todo,
    get_todos,
    update_todo,
    delete_todo,
    toggle_todo_complete,
)

__all__ = [
    "create_todo",
    "get_todo",
    "get_todos",
    "update_todo",
    "delete_todo",
    "toggle_todo_complete",
]
