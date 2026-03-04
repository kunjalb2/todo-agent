# Todo Agent - Chat Workflow Diagrams

> Visual representations of the agent/chat system architecture and data flows.

---

## 1. Complete System Architecture

```mermaid
graph TB
    subgraph "Client Side - Browser"
        UI[Chat UI Component]
        State[React State Management]
        APIClient[API Client Layer]
        CookieMgr[Cookie Manager]
    end

    subgraph "API Layer - Next.js"
        GetToken[/api/auth/get-token]
        SetToken[/api/auth/set-token]
    end

    subgraph "Network - HTTP/HTTPS"
        Request[HTTP Request + JWT]
        SSE[SSE Stream Response]
    end

    subgraph "Backend - FastAPI"
        Router[/agent/chat Router]
        Auth[Auth Middleware]
        Agent[Todo Agent]
        SessionMgr[Session Manager]
        ToolExecutor[Tool Executor]
        Guardrails[Input Guardrails]
    end

    subgraph "AI Services"
        LLM[OpenAI / OpenRouter API]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL Database)]
        Sessions[In-Memory Sessions]
    end

    %% Connections
    UI --> State
    State --> APIClient
    APIClient --> CookieMgr
    CookieMgr --> GetToken
    CookieMgr --> SetToken

    APIClient -->|POST /agent/chat| Request
    Request --> Router
    Router --> Auth
    Auth --> Agent

    Agent --> SessionMgr
    SessionMgr --> Sessions

    Agent --> Guardrails
    Agent --> ToolExecutor
    ToolExecutor --> DB
    Agent --> LLM
    LLM --> Agent

    Agent -->|Yield events| Router
    Router --> SSE
    SSE --> APIClient
    APIClient --> State
    State --> UI

    %% Styling
    classDef frontend fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef backend fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef database fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef ai fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef network fill:#fce4ec,stroke:#c2185b,stroke-width:2px

    class UI,State,APIClient,CookieMgr frontend
    class Router,Auth,Agent,SessionMgr,ToolExecutor,Guardrails backend
    class DB,Sessions database
    class LLM ai
    class Request,SSE network
```

---

## 2. Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    participant Browser as User Browser
    participant Frontend as Next.js Frontend
    participant CookieAPI as Cookie API Route
    participant Backend as FastAPI Backend
    participant DB as PostgreSQL

    Note over Browser,DB: LOGIN PROCESS (One-time)
    Browser->>Frontend: Enter credentials & submit
    Frontend->>Backend: POST /auth/login
    Backend->>DB: Validate credentials
    DB-->>Backend: User data
    Backend->>Backend: Generate JWT token
    Backend-->>Frontend: Return token + Set-Cookie
    Frontend->>CookieAPI: Store in HTTP-only cookie

    Note over Browser,DB: CHAT SESSION START
    Browser->>Frontend: Navigate to /agent
    Frontend->>CookieAPI: GET /api/auth/get-token
    CookieAPI->>CookieAPI: Read HTTP-only cookie
    CookieAPI-->>Frontend: Return JWT token
    Frontend->>Frontend: Store token in state

    Note over Browser,DB: SEND CHAT MESSAGE
    Browser->>Frontend: Type message, click Send
    Frontend->>Backend: POST /agent/chat<br/>Authorization: Bearer <JWT>
    Backend->>Backend: decode_access_token(JWT)
    Backend->>DB: SELECT * FROM users WHERE id = user_id
    DB-->>Backend: User object
    Backend->>Backend: Verify user exists
    Backend-->>Frontend: SSE Stream starts
```

---

## 3. Message Processing Flow

```mermaid
flowchart TD
    Start([User sends message]) --> Validate[Message validation]
    Validate -->|Invalid| Error1[Return error]
    Validate -->|Valid| AuthCheck[Check JWT token]

    AuthCheck -->|No token| Redirect[Redirect to /login]
    AuthCheck -->|Token exists| Decode[Decode JWT]

    Decode -->|Invalid token| Error2[Return 401 error]
    Decode -->|Valid token| GetUser[Get user from DB]

    GetUser -->|Not found| Error3[Return 401 error]
    GetUser -->|Found| GetSession[Get user session]

    GetSession --> CreateAgent[Create agent with user context]
    CreateAgent --> RunAgent[Run agent with streaming]

    RunAgent --> CheckTools{Does AI need<br/>to call tools?}

    CheckTools -->|No| StreamText[Stream text response]
    CheckTools -->|Yes| CallTool[Call tool function]

    CallTool --> DBQuery[Query database]
    DBQuery --> GetResult[Get result]
    GetResult --> ContinueAI[Continue AI with result]

    StreamText --> FormatEvent[Format as SSE event]
    ContinueAI --> FormatEvent
    FormatEvent --> SendEvent[Send to frontend]

    SendEvent --> MoreEvents{More events?}
    MoreEvents -->|Yes| StreamText
    MoreEvents -->|No| Done[Send "done" event]

    Done --> End([Complete])

    style Start fill:#c8e6c9
    style End fill:#c8e6c9
    style Error1 fill:#ffcdd2
    style Error2 fill:#ffcdd2
    style Error3 fill:#ffcdd2
    style Redirect fill:#ffcdd2
    style SendEvent fill:#fff9c4
    style Done fill:#b3e5fc
```

---

## 4. Server-Sent Events (SSE) Flow

```mermaid
sequenceDiagram
    autonumber
    participant UI as React UI
    participant API as API Client
    participant Network as HTTP Network
    participant Backend as FastAPI
    participant Agent as Todo Agent
    participant LLM as OpenAI API

    Note over UI,LLM: STREAMING INITIATION
    UI->>API: for await (event of chatStream())
    API->>Network: fetch(..., {method: 'POST'})
    Network->>Backend: POST /agent/chat
    Backend->>Agent: stream_agent_response()
    Agent->>LLM: Run with streaming enabled

    Note over UI,LLM: STREAMING LOOP
    activate LLM
    loop Each chunk
        LLM->>Agent: Response chunk
        Agent->>Agent: Process event type
        Agent->>Backend: Yield event dict
        Backend->>Backend: Format as SSE<br/>"data: {...}\n\n"
        Backend->>Network: Write to stream
        Network->>API: Read chunk from reader
        API->>API: Parse SSE data
        API->>UI: yield event
        UI->>UI: Update state
        UI->>UI: Re-render with new content
    end
    deactivate LLM

    Note over UI,LLM: COMPLETION
    Backend->>Network: Send "done" event
    Network->>API: Parse "done"
    API->>UI: yield done event
    UI->>UI: Final state update
    UI->>UI: Exit loop
```

---

## 5. Tool Execution Flow

```mermaid
flowchart TD
    Start([Agent determines tool needed]) --> GetContext[Get UserContext]

    GetContext --> Inject[Inject user_id into tool call]
    Inject --> ToolFunc[Call tool function]

    ToolFunc --> DBSession[Get DB session]
    DBSession --> Query[Build query with user_id filter]

    Query --> Execute[Execute SQL query]
    Execute --> Result[Get result from DB]

    Result --> Format{Is result<br/>successful?}

    Format -->|No| NotFound[Return "not found" message]
    Format -->|Yes| FormatSuccess[Format result for display]

    NotFound --> Return[Return formatted string to AI]
    FormatSuccess --> Return

    Return --> AIProcess[AI includes in response]
    AIProcess --> Stream[Stream to user]

    NotFound2{Is query result<br/>empty?} -->|Yes| EmptyMsg[Return "no todos" message]
    NotFound2 -->|No| BuildList[Build todo list]
    EmptyMsg --> Return
    BuildList --> Return

    style Start fill:#e1bee7
    style Stream fill:#c8e6c9
    style Return fill:#fff9c4
    style Query fill:#bbdefb
```

---

## 6. Session Management

```mermaid
graph TB
    subgraph "User Requests"
        U1[User 1: Request A]
        U2[User 2: Request X]
        U3[User 1: Request B]
        U4[User 3: Request Y]
    end

    subgraph "Session Storage (_user_sessions dict)"
        S1["Session 1:<br/>- Conversation history<br/>- Context"]
        S2["Session 2:<br/>- Conversation history<br/>- Context"]
        S3["Session 3:<br/>- Conversation history<br/>- Context"]
    end

    subgraph "AI Agent"
        AG[Todo Agent with<br/>OpenAIConversationsSession]
    end

    subgraph "Conversation Memory"
        M1["User 1 remembers:<br/>Previous messages<br/>Context awareness"]
        M2["User 2 remembers:<br/>Previous messages<br/>Context awareness"]
        M3["User 3 remembers:<br/>Previous messages<br/>Context awareness"]
    end

    U1 --> S1
    U2 --> S2
    U3 --> S1
    U4 --> S3

    S1 --> AG
    S2 --> AG
    S3 --> AG

    S1 -.->|maintains| M1
    S2 -.->|maintains| M2
    S3 -.->|maintains| M3

    style U1 fill:#e3f2fd
    style U2 fill:#e3f2fd
    style U3 fill:#e3f2fd
    style U4 fill:#e3f2fd
    style S1 fill:#fff3e0
    style S2 fill:#fff3e0
    style S3 fill:#fff3e0
    style M1 fill:#e8f5e9
    style M2 fill:#e8f5e9
    style M3 fill:#e8f5e9
```

---

## 7. Event Types Flow

```mermaid
stateDiagram-v2
    [*] --> Idle: User lands on page

    Idle --> Validating: User types & submits
    Validating --> Authenticated: Token valid
    Validating --> Error: Token invalid

    Authenticated --> Streaming: API call successful

    state Streaming {
        [*] --> ContentReceiving
        ContentReceiving --> ContentReceiving: content event
        ContentReceiving --> ToolCalling: tool_call event
        ToolCalling --> ToolRunning: Waiting for result
        ToolRunning --> ToolResult: tool_result event
        ToolResult --> ContentReceiving: More content
        ContentReceiving --> Done: done event
        ContentReceiving --> Error: error event
    }

    Streaming --> Complete: done event received
    Streaming --> ShowError: error event
    ShowError --> Complete
    Complete --> Idle: Ready for next message
    Error --> Idle: Redirect to login

    note right of ContentReceiving
        Text chunks streamed
        in real-time
    end note

    note right of ToolCalling
        AI decides to use
        a tool function
    end note

    note right of ToolResult
        Tool execution
        completed
    end note
```

---

## 8. Database Layer Interaction

```mermaid
flowchart LR
    subgraph "Tool Functions"
        T1[get_todos]
        T2[create_todo]
        T3[update_todo]
        T4[delete_todo]
        T5[complete_todo]
    end

    subgraph "Database Access"
        AS[async_session_maker]
        SES[AsyncSession]
    end

    subgraph "SQLAlchemy ORM"
        Q[Query Builder]
        M[Todo Model]
    end

    subgraph "PostgreSQL"
        DB[(Database)]

        subgraph "Tables"
            TM[todos table]
            UM[users table]
        end
    end

    T1 --> AS
    T2 --> AS
    T3 --> AS
    T4 --> AS
    T5 --> AS

    AS --> SES
    SES --> Q
    Q --> M
    M --> DB

    DB --> Q
    Q --> SES
    SES --> T1
    SES --> T2
    SES --> T3
    SES --> T4
    SES --> T5

    style T1 fill:#e1f5fe
    style T2 fill:#e1f5fe
    style T3 fill:#e1f5fe
    style T4 fill:#e1f5fe
    style T5 fill:#e1f5fe
    style DB fill:#c8e6c9
```

---

## 9. Complete Data Structure Flow

```mermaid
flowchart TD
    subgraph "Frontend State"
        FM["messages: Message[]<br/>[{<br/>  role: 'user' | 'assistant',<br/>  content: string,<br/>  toolCalls?: ToolCall[],<br/>  timestamp: Date<br/>}]"]
    end

    subgraph "API Request"
        REQ["POST /agent/chat<br/>{<br/>  message: string,<br/>  stream: boolean<br/>}"]
    end

    subgraph "SSE Events"
        EVT["Event Types:<br/>- {type: 'content', content: string}<br/>- {type: 'tool_call', tool, args}<br/>- {type: 'tool_result', result}<br/>- {type: 'error', content}<br/>- {type: 'done'}"]
    end

    subgraph "Backend Processing"
        USR["User: {id, email, password_hash}"]
        CTX["UserContext: {user_id, name}"]
        CFG["RunConfig: {model_provider, ...}"]
    end

    subgraph "Database Models"
        TODO["Todo: {<br/>  id: int,<br/>  user_id: int,<br/>  title: str,<br/>  description: str,<br/>  due_date: datetime,<br/>  priority: Priority,<br/>  is_completed: bool,<br/>  created_at: datetime<br/>}"]
    end

    FM --> REQ
    REQ --> EVT
    EVT --> USR
    USR --> CTX
    CTX --> CFG
    CFG --> TODO

    style FM fill:#e3f2fd
    style REQ fill:#fff3e0
    style EVT fill:#f3e5f5
    style USR fill:#e8f5e9
    style TODO fill:#ffebee
```

---

## 10. Error Handling Flow

```mermaid
flowchart TD
    Start([User Action]) --> FE Try{Frontend<br/>Try/Catch}
    FE Try -->|Success| APICall[Make API Call]
    FE Try -->|Error| FEError[Show error in UI]

    APICall --> BE Try{Backend<br/>Try/Catch}
    BE Try -->|Success| AgentRun[Run Agent]
    BE Try -->|Error| BEError1[Yield error event]

    AgentRun --> AgentTry{Agent<br/>Try/Catch}
    AgentTry -->|Success| LLMCall[Call LLM]
    AgentTry -->|Error| BEError2[Yield error event]

    LLMCall --> ToolTry{Tool<br/>Try/Catch}
    ToolTry -->|Success| DBQuery[Query DB]
    ToolTry -->|Error| ToolError[Return error message]

    DBQuery --> DBCheck{DB<br/>Error?}
    DBCheck -->|No| Success[Return result]
    DBCheck -->|Yes| DBError[Log error, return None]

    Success --> Stream[Stream result]
    ToolError --> Stream
    Stream --> End([Complete])

    BEError1 --> SSEError[Send SSE error]
    BEError2 --> SSEError
    SSEError --> End
    FEError --> End

    style Start fill:#c8e6c9
    style End fill:#c8e6c9
    style FEError fill:#ffcdd2
    style BEError1 fill:#ffcdd2
    style BEError2 fill:#ffcdd2
    style ToolError fill:#ffcdd2
    style DBError fill:#ffcdd2
    style Success fill:#c8e6c9
    style Stream fill:#b3e5fc
```

---

*These diagrams are interactive in compatible markdown viewers. For the best viewing experience, use a markdown renderer that supports Mermaid.js.*
