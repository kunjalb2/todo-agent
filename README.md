# Todo Agent Application

A full-stack Todos & Tasks Management Application with an AI Agent Chat Interface. The application features JWT-based authentication, CRUD operations for todos with filtering, and an AI agent that can answer IT/coding questions and manage todos via natural language.

## Documentation

For detailed understanding of the agent/chat workflow, see:
- **[Agent Chat Workflow Documentation](docs/AGENT_CHAT_WORKFLOW.md)** - Complete end-to-end workflow guide
- **[Agent Chat Diagrams](docs/AGENT_CHAT_DIAGRAMS.md)** - Visual architecture and flow diagrams
- **[Agent Chat Quick Reference](docs/AGENT_CHAT_QUICK_REF.md)** - Simplified beginner-friendly guide

## Features

- **Authentication**: JWT-based user registration and login
- **Todo Management**: Create, read, update, delete, and mark todos as complete
- **Filtering**: Filter todos by date range and completion status
- **AI Chat Agent**: Natural language interface to:
  - Answer IT and coding questions
  - Create and manage todos
  - Provide explanations and code examples
- **Guardrails**: AI agent stays focused on IT, coding, and task management topics
- **Provider Flexibility**: Switch between OpenRouter and OpenAI via environment variables
- **Real-time Streaming**: Server-Sent Events (SSE) for instant AI responses

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy (async) + Alembic migrations
- **Auth**: JWT with bcrypt password hashing
- **AI**: `openai-agents` Python SDK

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Markdown**: react-markdown with syntax highlighting

## Project Structure

```
todo-agent/
├── backend/
│   ├── alembic/              # Database migrations
│   ├── app/
│   │   ├── agent/            # AI agent implementation
│   │   ├── api/              # API endpoints
│   │   ├── core/             # Config, security
│   │   ├── crud/             # Database operations
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   └── main.py           # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages
│   │   ├── components/       # React components
│   │   └── lib/              # Utilities, API client
│   └── package.json
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### 1. Database Setup

Start PostgreSQL and create a database:

```bash
# On macOS with Homebrew
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

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000
API docs: http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit if needed (defaults to http://localhost:8000)

# Start dev server
npm run dev
```

The app will be available at http://localhost:3000

### 4. Environment Configuration

#### Backend (.env)

```bash
# Application
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/todoagent

# JWT
JWT_SECRET_KEY=your-secret-key-min-32-characters
JWT_EXPIRATION_MINUTES=10080

# LLM Provider
# Options: "openrouter" or "openai"
PROVIDER=openrouter

# OpenRouter (recommended)
OPENROUTER_API_KEY=your-openrouter-key
DEFAULT_OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# OpenAI (alternative)
OPENAI_API_KEY=your-openai-key
DEFAULT_OPENAI_MODEL=gpt-4o-mini
```

#### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Usage

1. **Register**: Create a new account at http://localhost:3000/register
2. **Dashboard**: View and manage your todos
3. **AI Chat**: Interact with the AI agent to:
   - Ask coding questions
   - Create todos naturally ("Add a todo to review the PR by Friday")
   - Get task status ("What are my pending todos?")

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get token
- `GET /auth/me` - Get current user

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

## Development

### Backend Development

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Frontend Development

```bash
# Build for production
npm run build

# Start production server
npm start
```

## License

MIT
