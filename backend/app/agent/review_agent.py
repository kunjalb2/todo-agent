"""Code Review Agent implementation with conversation management."""
import json
from typing import AsyncIterator

from agents import Agent, Runner, OpenAIProvider, RunConfig, RunContextWrapper
from openai import AsyncOpenAI
from sqlalchemy import select

from app.agent.config import get_llm_client, get_model_name
from app.agent.review_tools import (
    list_reviewable_files,
    review_code_snippet,
    review_file,
    review_git_diff,
)
from app.database import async_session_maker
from app.models.user import User


# User context for dynamic instructions
class ReviewContext:
    """Context object containing user information for code review."""
    def __init__(self, user_id: int, first_name: str = "", last_name: str = ""):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.name = f"{first_name} {last_name}".strip() or f"User {user_id}"


# Store conversation history per user for review agent
_review_user_history: dict[int, list] = {}


def get_review_user_history(user_id: int) -> list:
    """Get review conversation history for a user."""
    if user_id not in _review_user_history:
        _review_user_history[user_id] = []
    return _review_user_history[user_id]


def reset_review_user_history(user_id: int) -> None:
    """Reset review conversation history for a user."""
    if user_id in _review_user_history:
        _review_user_history[user_id] = []


def get_review_instructions(
    context: RunContextWrapper[ReviewContext],
    agent: Agent[ReviewContext],
) -> str:
    """Dynamic instructions for the code review agent.

    Args:
        context: The run context wrapper containing user information
        agent: The agent instance

    Returns:
        Instructions string with user context injected
    """
    instructions = (
        "You are an expert Code Review AI assistant. You help developers improve their code "
        "by providing comprehensive, actionable feedback.\n\n"
        "Your expertise includes:\n"
        "- Security: Detecting vulnerabilities, injection risks, authentication issues\n"
        "- Bugs: Finding logic errors, edge cases, race conditions, resource leaks\n"
        "- Style: Code formatting, naming conventions, readability improvements\n"
        "- Architecture: Design patterns, separation of concerns, maintainability\n"
        "- Performance: Optimization opportunities, algorithm efficiency, resource usage\n"
        "- Best Practices: Language-specific idioms, framework conventions, standards\n\n"
        "When reviewing code, provide:\n"
        "1. **Severity Levels**: Critical, High, Medium, Low, Info\n"
        "2. **Specific Locations**: File paths and line numbers when applicable\n"
        "3. **Clear Explanations**: Why something is an issue\n"
        "4. **Actionable Suggestions**: How to fix each issue\n"
        "5. **Code Examples**: Show improved code when helpful\n\n"
        "Format your reviews with:\n"
        "- Clear section headers\n"
        "- Severity badges (🔴 Critical, 🟠 High, 🟡 Medium, 🔵 Low, ⚪ Info)\n"
        "- Code blocks with syntax highlighting\n"
        "- Summary at the end\n\n"
        "Be constructive and educational. Help the user learn, not just fix issues."
    )

    user_info = (
        f"\n\nIMPORTANT: You are assisting {context.context.name} (user ID: {context.context.user_id}). "
        f"When calling review tools, always use user_id={context.context.user_id} automatically. "
        f"Do NOT ask the user for their user ID - you already know it. "
        f"Address the user by their name ({context.context.name}) when appropriate to make the conversation more personal."
    )

    return instructions + user_info


def create_review_agent() -> Agent[ReviewContext]:
    """Create the code review agent with tools and dynamic instructions."""

    return Agent[ReviewContext](
        name="ReviewAgent",
        instructions=get_review_instructions,
        model=get_model_name(),
        tools=[
            review_code_snippet,
            review_file,
            review_git_diff,
            list_reviewable_files,
        ],
    )


async def stream_review_response(
    user_id: int,
    message: str,
) -> AsyncIterator[dict]:
    """Stream review agent response for a user message.

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

    agent = create_review_agent()
    review_context = ReviewContext(user_id, first_name, last_name)

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
            context=review_context,
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


async def get_review_response(user_id: int, message: str) -> str:
    """Get a non-streamed review agent response (fallback).

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

    agent = create_review_agent()
    review_context = ReviewContext(user_id, first_name, last_name)

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
            context=review_context,
            run_config=run_config,
        )

        # Get the final output as a string
        output = result.final_output_as(str)

        if output is None:
            return "I apologize, but I couldn't generate a review. Please try again."

        return output

    except Exception as e:
        return f"Error: {str(e)}"
