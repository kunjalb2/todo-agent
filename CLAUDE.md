# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Full-stack Todo application with dual AI agents: a Todo Agent for task management and IT/coding Q&A, and a Code Review Agent for automated code analysis.

## Documentation

For detailed understanding of the agent/chat workflow, see:
- **[Agent Chat Workflow](docs/AGENT_CHAT_WORKFLOW.md)** - Complete end-to-end workflow guide
- **[Agent Chat Diagrams](docs/AGENT_CHAT_DIAGRAMS.md)** - Visual architecture and flow diagrams
- **[Agent Chat Quick Reference](docs/AGENT_CHAT_QUICK_REF.md)** - Simplified beginner-friendly guide

## Common Commands

### Backend (FastAPI)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run production server
npm start

# Lint
npm run lint
```

### Database Setup

```bash
# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql@14
createdb todoagent

# Or using Docker
docker run -d --name postgres-todoagent \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=todoagent \
  -p 5432:5432 \
  postgres:14-alpine
```

## Architecture

### Backend Structure (`backend/app/`)

- **`main.py`** - FastAPI application entry point, includes routers and CORS middleware
- **`database.py`** - Async SQLAlchemy engine and session factory (`async_session_maker`, `get_db()`)
- **`core/`** - Configuration (`config.py` uses Pydantic Settings) and JWT security (`security.py`)
- **`models/`** - SQLAlchemy ORM models (User with first_name/last_name, Todo with Priority enum)
- **`schemas/`** - Pydantic schemas for request/response validation
- **`crud/`** - Database operations (todo.py contains create, read, update, delete functions)
- **`api/`** - FastAPI routers (auth.py, todos.py, agent.py, review.py)
- **`dependencies.py`** - FastAPI dependency injection (`CurrentUserDep`, `DbDep` type aliases)

### Agent Implementation (`backend/app/agent/`)

The AI agents are built with `openai-agents` SDK:

#### Todo Agent (`agent.py`)
- Main agent with streaming support, conversation sessions, function tools
- User-specific conversation sessions stored in `_user_sessions` dict
- Dynamic instructions inject `user_id`, `first_name`, `last_name` into agent context (auto-passed to tools)
- Streaming via Server-Sent Events (SSE) with event types: `content`, `tool_call`, `tool_result`, `done`, `error`
- Tools: `list_todos`, `add_todo`, `modify_todo`, `remove_todo`, `mark_complete`

#### Review Agent (`review_agent.py`)
- Dedicated code review agent with separate session storage (`_review_user_sessions`)
- No database tools - focuses on code analysis via file operations
- Tools: `list_reviewable_files`, `review_code_snippet`, `review_file`, `review_git_diff`
- Uses severity levels: Critical, High, Medium, Low, Info

#### Shared Components
- **`tools.py`** - Database-level functions for todo operations (used by todo agent tools)
- **`review_tools.py`** - File-system level functions for code review operations
- **`guardrails.py`** - Input guardrails for topic filtering (IT, coding, task management only)
- **`config.py`** - LLM client factory (supports OpenRouter and OpenAI via `PROVIDER` env var)

### Frontend Structure (`frontend/src/`)

- **`app/`** - Next.js App Router pages (`/dashboard`, `/agent`, `/review`, `/profile`, `/login`, `/register`)
- **`components/`** - React components (dashboard/ for todo UI, ui/ for shadcn components)
- **`lib/api.ts`** - Axios API client with JWT token handling
- **`middleware.ts`** - Auth middleware protecting `/dashboard`, `/agent`, `/review`, and `/profile` routes

### Authentication Flow

1. JWT tokens stored in HTTP-only `access_token` cookie
2. Frontend uses Next.js API routes (`/api/auth/set-token`, `/api/auth/get-token`) to manage cookies
3. Backend validates JWT via `HTTPBearer` in `dependencies.py:get_current_user()`
4. Protected routes redirect to `/login` if no token

### Environment Configuration

**Backend (.env):**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Minimum 32 characters
- `PROVIDER` - "openrouter" or "openai"
- `OPENROUTER_API_KEY` / `OPENAI_API_KEY` - LLM provider credentials
- `MODEL_NAME` - Optional model override

**Frontend (.env.local):**
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

## Agent Tool Patterns

When adding new tools to agents:
1. Import `function_tool` from `agents.tool` (required for decorator)
2. Define the tool function with `@function_tool` decorator in `agent.py` or `review_agent.py`
3. Include `user_id: int` as the first parameter (injected automatically via context)
4. Implement the actual operation in `tools.py` or `review_tools.py`
5. Return formatted string responses for natural language presentation
6. Tools are automatically passed `user_id` from the dynamic instructions context

**Important:** The `function_tool` import must be added explicitly:
```python
from agents.tool import function_tool
```

## User Context & Personalization

The User model includes `first_name` and `last_name` fields. When working with user context:

1. **UserContext Class** (`agent.py`, `review_agent.py`): Accepts `user_id`, `first_name`, `last_name`
2. **Dynamic Instructions**: Inject user's actual name into AI responses ("Hello John!" instead of "Hello User 123")
3. **Fetching User Data**: Agents fetch user data from DB before processing to get names
4. **Profile Management**: Users can update their name via `/profile` route (email is read-only)

## SSE (Server-Sent Events) Streaming Pattern

The chat endpoint uses SSE for real-time streaming. Event format:
```
data: {"type": "content", "content": "Hello"}\n\n
data: {"type": "tool_call", "tool": "add_todo", "args": {...}}\n\n
data: {"type": "done"}\n\n
```

**Frontend parsing** (`lib/api.ts`): Read from `response.body`, split by `\n`, parse lines starting with `data: `

**Backend event generation** (`agent.py`):
- `raw_response_event` → text deltas
- `run_item_stream_event` → tool calls/results
- Wrap each event in `json.dumps()` and prefix with `data: `

## Database Schema

**Users Table:**
- `id` (PK), `first_name`, `last_name`, `email` (unique), `hashed_password`, `created_at`
- `full_name` property returns "first_name last_name"

**Todos Table:**
- `id` (PK), `user_id` (FK → users.id), `title`, `description`, `due_date`, `priority` (enum: low/medium/high), `is_completed`, `created_at`, `updated_at`
- All todo operations MUST filter by `user_id` for data isolation

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user (requires first_name, last_name, email, password)
- `POST /auth/login` - Login and get token
- `GET /auth/me` - Get current user info
- `PUT /auth/profile` - Update first_name and last_name
- `PUT /auth/change-password` - Change password (requires current_password, new_password)

### Todos
- `GET /todos` - List todos (with optional filters)
- `POST /todos` - Create todo
- `GET /todos/{id}` - Get single todo
- `PUT /todos/{id}` - Update todo
- `DELETE /todos/{id}` - Delete todo
- `PATCH /todos/{id}/complete` - Toggle completion

### Agent
- `POST /agent/chat` - Chat with AI (streaming)
- `POST /agent/reset` - Reset conversation

### Review
- `POST /review/chat` - Code review with streaming
- `POST /review/reset` - Reset review conversation
