"""Agent API endpoints with streaming support."""
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.agent import (
    get_agent_response,
    reset_user_history,
    stream_agent_response,
)
from app.dependencies import CurrentUserDep

router = APIRouter(prefix="/agent", tags=["Agent"])


class ChatRequest(BaseModel):
    """Chat request schema."""

    message: str
    stream: bool = True


class ChatResponse(BaseModel):
    """Non-streamed chat response schema."""

    response: str


@router.post("/chat", response_model=None)
async def chat_endpoint(
    request: ChatRequest,
    current_user: CurrentUserDep,
) -> StreamingResponse | ChatResponse:
    """Chat with the AI agent."""

    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        try:
            async for event in stream_agent_response(current_user.id, request.message):
                # Format as SSE
                event_data = json.dumps(event)
                yield f"data: {event_data}\n\n"

            # Send completion event
            yield "data: {\"type\": \"done\"}\n\n"

        except Exception as e:
            error_event = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {error_event}\n\n"

    if request.stream:
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming fallback
    response = await get_agent_response(current_user.id, request.message)
    return ChatResponse(response=response)


@router.post("/reset")
async def reset_chat_endpoint(
    current_user: CurrentUserDep,
) -> dict:
    """Reset the chat history for the current user."""
    reset_user_history(current_user.id)
    return {"message": "Chat history reset"}


@router.get("/test-stream")
async def test_stream(current_user: CurrentUserDep) -> StreamingResponse:
    """Test endpoint to verify SSE streaming works."""
    async def generate() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'info', 'message': 'Stream started'})}\n\n"
        await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'type': 'info', 'message': 'Stream test 1'})}\n\n"
        await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'type': 'info', 'message': 'Stream test 2'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


