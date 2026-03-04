"""Code Review API endpoints with streaming support."""
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.review_agent import (
    get_review_response,
    reset_review_user_history,
    stream_review_response,
)
from app.dependencies import CurrentUserDep

router = APIRouter(prefix="/review", tags=["Review"])


# Request/Response Schemas
class ChatRequest(BaseModel):
    """Chat request schema for review agent."""
    message: str
    stream: bool = True


class ChatResponse(BaseModel):
    """Non-streamed chat response schema."""
    response: str


class SnippetReviewRequest(BaseModel):
    """Request to review a code snippet."""
    code: str
    language: str = "python"
    focus_areas: str = "security,bugs,style,best_practices"


class FileReviewRequest(BaseModel):
    """Request to review a file."""
    file_path: str
    focus_areas: str = "security,bugs,style,best_practices"


class GitDiffReviewRequest(BaseModel):
    """Request to review git diff."""
    staged_only: bool = False
    focus_areas: str = "security,bugs,style,best_practices"


class FileListRequest(BaseModel):
    """Request to list reviewable files."""
    directory: str = "."
    max_depth: int = 3


class ReviewIssue(BaseModel):
    """A single review issue."""
    severity: str = Field(..., description="Critical, High, Medium, Low, or Info")
    category: str = Field(..., description="security, bugs, style, etc.")
    line: int | None = Field(None, description="Line number if applicable")
    message: str = Field(..., description="Issue description")
    suggestion: str | None = Field(None, description="Suggested fix")


class ReviewResult(BaseModel):
    """Result of a code review."""
    summary: str
    issues: list[ReviewIssue]
    overall_score: int | None = Field(None, description="0-100 score, optional")


class FileNode(BaseModel):
    """A node in the file tree."""
    name: str
    path: str
    type: str = Field(..., description="file or directory")
    children: list["FileNode"] = []


# Update forward references for FileNode
FileNode.model_rebuild()


@router.post("/chat", response_model=None)
async def review_chat_endpoint(
    request: ChatRequest,
    current_user: CurrentUserDep,
) -> StreamingResponse | ChatResponse:
    """Chat with the code review agent."""

    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        try:
            async for event in stream_review_response(current_user.id, request.message):
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
    response = await get_review_response(current_user.id, request.message)
    return ChatResponse(response=response)


@router.post("/snippet")
async def review_snippet_endpoint(
    request: SnippetReviewRequest,
    current_user: CurrentUserDep,
) -> ChatResponse:
    """Review a code snippet (one-shot)."""
    message = (
        f"Please review this {request.language} code snippet "
        f"focusing on: {request.focus_areas}\n\n"
        f"```{request.language}\n{request.code}\n```"
    )

    response = await get_review_response(current_user.id, message)
    return ChatResponse(response=response)


@router.post("/file")
async def review_file_endpoint(
    request: FileReviewRequest,
    current_user: CurrentUserDep,
) -> ChatResponse:
    """Review a file by path."""
    message = (
        f"Please review the file `{request.file_path}` "
        f"focusing on: {request.focus_areas}"
    )

    response = await get_review_response(current_user.id, message)
    return ChatResponse(response=response)


@router.post("/git")
async def review_git_endpoint(
    request: GitDiffReviewRequest,
    current_user: CurrentUserDep,
) -> ChatResponse:
    """Review git diff changes."""
    diff_type = "staged" if request.staged_only else "unstaged"
    message = (
        f"Please review my {diff_type} git changes "
        f"focusing on: {request.focus_areas}"
    )

    response = await get_review_response(current_user.id, message)
    return ChatResponse(response=response)


@router.post("/files")
async def list_files_endpoint(
    request: FileListRequest,
    current_user: CurrentUserDep,
) -> ChatResponse:
    """List reviewable files in the project."""
    message = (
        f"List all reviewable files in the `{request.directory}` directory. "
        f"Use max_depth={request.max_depth}."
    )

    response = await get_review_response(current_user.id, message)
    return ChatResponse(response=response)


@router.post("/reset")
async def reset_review_chat_endpoint(
    current_user: CurrentUserDep,
) -> dict:
    """Reset the review chat history for the current user."""
    reset_review_user_history(current_user.id)
    return {"message": "Review chat history reset"}
