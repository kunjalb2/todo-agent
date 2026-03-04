"""AI Agent implementation with conversation management."""
import json
from typing import AsyncIterator

from agents import Agent, Runner, OpenAIProvider, RunConfig, RunContextWrapper
from agents.tool import function_tool
from openai import AsyncOpenAI
from sqlalchemy import select

from app.agent.config import get_llm_client, get_model_name
from app.agent.guardrails import create_topic_guardrail
from app.agent.tools import (
    complete_todo,
    create_todo,
    delete_todo,
    get_todos,
    update_todo,
)
from app.database import async_session_maker
from app.models.user import User


# User context for dynamic instructions
class UserContext:
    """Context object containing user information."""
    def __init__(self, user_id: int, first_name: str = "", last_name: str = ""):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.name = f"{first_name} {last_name}".strip() or f"User {user_id}"


# Store conversation history per user (simple in-memory storage)
_user_history: dict[int, list] = {}


def get_user_history(user_id: int) -> list:
    """Get conversation history for a user."""
    if user_id not in _user_history:
        _user_history[user_id] = []
    return _user_history[user_id]


def reset_user_history(user_id: int) -> None:
    """Reset conversation history for a user."""
    if user_id in _user_history:
        _user_history[user_id] = []


# Define agent tools
@function_tool
async def list_todos(user_id: int, completed_only: bool | None = None) -> str:
    """List all todos for the current user.

    Args:
        user_id: The ID of the current user
        completed_only: If True, only show completed todos. If False, only show incomplete todos.

    Returns:
        A formatted string with all todos
    """
    result = await get_todos(user_id, completed_only)

    if not result["todos"]:
        return "You don't have any todos yet."

    todos_text = []
    for todo in result["todos"]:
        status = "✓" if todo["is_completed"] else "○"
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(todo["priority"], "")
        due_str = f" (due: {todo['due_date'][:10]})" if todo["due_date"] else ""
        desc = f" - {todo['description']}" if todo["description"] else ""

        todos_text.append(f"{status} {priority_emoji} **{todo['title']}**{desc}{due_str}")

    summary = f"\n\nSummary: {result['completed']}/{result['total']} completed"
    return "\n".join(todos_text) + summary


@function_tool
async def add_todo(
    user_id: int,
    title: str,
    description: str | None = None,
    due_date: str | None = None,
    priority: str = "medium",
) -> str:
    """Create a new todo.

    Args:
        user_id: The ID of the current user
        title: The title of the todo
        description: Optional description
        due_date: Optional due date (ISO format or YYYY-MM-DD)
        priority: Priority level (low, medium, high)

    Returns:
        Confirmation message
    """
    result = await create_todo(user_id, title, description, due_date, priority)
    return f"Created new todo: **{result['title']}** (ID: {result['id']})"


@function_tool
async def modify_todo(
    user_id: int,
    todo_id: int,
    title: str | None = None,
    description: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    is_completed: bool | None = None,
) -> str:
    """Update an existing todo.

    Args:
        user_id: The ID of the current user
        todo_id: The ID of the todo to update
        title: New title
        description: New description
        due_date: New due date (ISO format or YYYY-MM-DD)
        priority: New priority (low, medium, high)
        is_completed: New completion status

    Returns:
        Confirmation message
    """
    result = await update_todo(user_id, todo_id, title, description, due_date, priority, is_completed)

    if not result:
        return f"Todo with ID {todo_id} not found."

    return f"Updated todo: **{result['title']}**"


@function_tool
async def remove_todo(user_id: int, todo_id: int) -> str:
    """Delete a todo.

    Args:
        user_id: The ID of the current user
        todo_id: The ID of the todo to delete

    Returns:
        Confirmation message
    """
    result = await delete_todo(user_id, todo_id)

    if not result["success"]:
        return f"Todo with ID {todo_id} not found."

    return "Todo deleted successfully."


@function_tool
async def mark_complete(user_id: int, todo_id: int) -> str:
    """Mark a todo as complete.

    Args:
        user_id: The ID of the current user
        todo_id: The ID of the todo to mark complete

    Returns:
        Confirmation message
    """
    result = await complete_todo(user_id, todo_id)

    if not result:
        return f"Todo with ID {todo_id} not found."

    return f"Marked **{result['title']}** as complete!"


def get_dynamic_instructions(
    context: RunContextWrapper[UserContext], agent: Agent[UserContext]
) -> str:
    """Dynamic instructions that include user context.

    Args:
        context: The run context wrapper containing user information
        agent: The agent instance

    Returns:
        Instructions string with user context injected
    """
    base_instructions = (
        "You are a helpful AI assistant for a Todo application. You can help users with:\n"
        "1. IT and coding questions (Python, JavaScript, databases, APIs, etc.)\n"
        "2. Managing their todos (create, update, delete, complete)\n"
        "3. Task management and productivity advice\n\n"
        "When users ask about todos, use the available tools to help them. "
        "For code review requests, inform users that they should use the dedicated Code Review Agent at the /review endpoint. "
        "Be concise and friendly in your responses. "
        "For coding questions, provide clear explanations and code examples when helpful. "
        "Always format code blocks with the appropriate language syntax."
    )

    user_info = (
        f"\n\nIMPORTANT: You are assisting {context.context.name} (user ID: {context.context.user_id}). "
        f"When calling todo tools, always use user_id={context.context.user_id} automatically. "
        f"Do NOT ask the user for their user ID - you already know it. "
        f"Address the user by their name ({context.context.name}) when appropriate to make the conversation more personal."
    )

    return base_instructions + user_info


def create_agent() -> Agent[UserContext]:
    """Create the AI agent with tools, guardrails, and dynamic instructions."""

    return Agent[UserContext](
        name="TodoAgent",
        instructions=get_dynamic_instructions,
        model=get_model_name(),
        tools=[
            list_todos,
            add_todo,
            modify_todo,
            remove_todo,
            mark_complete,
        ],
        input_guardrails=[create_topic_guardrail()],
    )


async def stream_agent_response(
    user_id: int,
    message: str,
) -> AsyncIterator[dict]:
    """Stream agent response for a user message.

    Args:
        user_id: The ID of the user
        message: The user's message

    Yields:
        Events containing content, tool calls, and completion status
    """
    # Fetch user data from database
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        first_name = user.first_name if user else ""
        last_name = user.last_name if user else ""

    agent = create_agent()
    user_context = UserContext(user_id, first_name, last_name)

    # Get the configured LLM client
    client = get_llm_client()

    # Create a run config with the OpenAI provider
    run_config = RunConfig(
        model_provider=OpenAIProvider(openai_client=client),
        tracing_disabled=True,
    )

    try:
        # Run the agent with streaming and user context
        result_streaming = Runner.run_streamed(
            starting_agent=agent,
            input=message,
            context=user_context,
            run_config=run_config,
        )

        # Stream events
        async for event in result_streaming.stream_events():
            # Handle different event types from openai-agents
            if hasattr(event, "type"):
                if event.type == "raw_response_event":
                    # Raw LLM response events - extract text deltas
                    if hasattr(event, "data") and hasattr(event.data, "type"):
                        if event.data.type == "response.output_text.delta":
                            # Text delta event
                            if hasattr(event.data, "delta"):
                                yield {
                                    "type": "content",
                                    "content": event.data.delta,
                                }

                elif event.type == "run_item_stream_event":
                    # Agent-level events (tool calls, outputs, messages)
                    if hasattr(event, "data"):
                        if hasattr(event.data, "name"):
                            if event.data.name == "tool_called":
                                # Tool is being called
                                if hasattr(event.data, "raw_item"):
                                    raw_item = event.data.raw_item
                                    tool_name = raw_item.name if hasattr(raw_item, "name") else "unknown"
                                    tool_args = raw_item.arguments if hasattr(raw_item, "arguments") else "{}"
                                    yield {
                                        "type": "tool_call",
                                        "tool": tool_name,
                                        "args": json.dumps(json.loads(tool_args) if isinstance(tool_args, str) else tool_args),
                                    }

                            elif event.data.name == "tool_output":
                                # Tool returned output
                                if hasattr(event.data, "output"):
                                    yield {
                                        "type": "tool_result",
                                        "result": str(event.data.output)[:500],
                                    }

                            elif event.data.name == "message_output_created":
                                # Final message created - extract full text
                                if hasattr(event.data, "raw_item") and hasattr(event.data.raw_item, "content"):
                                    for content_item in event.data.raw_item.content:
                                        if hasattr(content_item, "text"):
                                            yield {
                                                "type": "content",
                                                "content": content_item.text,
                                            }

                elif event.type == "agent_updated_stream_event":
                    # Agent state updates - skip
                    continue

                elif event.type == "done":
                    # Already handled below
                    pass

        # Yield completion event
        yield {
            "type": "done",
            "content": None,
        }

    except Exception as e:
        yield {
            "type": "error",
            "content": str(e),
        }


async def get_agent_response(user_id: int, message: str) -> str:
    """Get a non-streamed agent response (fallback).

    Args:
        user_id: The ID of the user
        message: The user's message

    Returns:
        The agent's response
    """
    # Fetch user data from database
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        first_name = user.first_name if user else ""
        last_name = user.last_name if user else ""

    agent = create_agent()
    user_context = UserContext(user_id, first_name, last_name)

    # Get the configured LLM client
    client = get_llm_client()

    # Create a run config with the OpenAI provider
    run_config = RunConfig(
        model_provider=OpenAIProvider(openai_client=client),
        tracing_disabled=True,
    )

    try:
        # Run the agent without streaming and user context
        result = await Runner.run(
            starting_agent=agent,
            input=message,
            context=user_context,
            run_config=run_config,
        )

        # Get the final output as a string
        output = result.final_output_as(str)

        if output is None:
            return "I apologize, but I couldn't generate a response. Please try again."

        return output

    except Exception as e:
        return f"Error: {str(e)}"
