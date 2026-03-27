# Architecture and the "Why" Behind the Technical Decisions

## Main Message of This Section

Do not describe the architecture as a shopping list of frameworks.

A strong architecture explanation answers this question:

"Why is the system shaped this way?"

That means every major component should be explained in terms of:

1. responsibility
2. benefit
3. tradeoff

## Short Architecture Summary

"The system uses a Next.js frontend for the user experience, a FastAPI backend for the scanning and API layer, SQLAlchemy with SQLite for persistence, modular scanner classes for each OWASP category, WebSockets for live scan progress, and server-sent events for streaming AI chat responses. I chose this architecture to keep the system modular, responsive, and easy to extend."

## End-to-End Request Flow

Walk through the system like this:

1. The user enters a target URL in the frontend.
2. The frontend calls `POST /api/scans`.
3. The backend validates the input and checks that the user confirmed authorization.
4. A `Scan` record is created in the database.
5. A background task launches the scan orchestrator.
6. The orchestrator runs each scanner module against the target.
7. Findings are persisted to the database.
8. Real-time progress is sent to the frontend through a WebSocket.
9. The frontend shows scan status, findings, and severity summaries.
10. After the scan completes, the user can open the chat view and ask the AI assistant about the results.

That flow is easy for a security manager to follow because it maps technical components to observable product behavior.

## Major Architectural Components

### 0. GitHub Actions as Part of the Architecture

Relevant code:

- `.github/workflows/pr-security.yml`
- `.github/semgrep/agentic-pr.yml`
- `backend/app/sast/cli.py`
- `backend/app/sast/diff_engine.py`
- `backend/app/sast/normalize.py`

This belongs in the architecture discussion because the system is not only a runtime application.

It also has a pull-request security pipeline.

That workflow:

1. checks out the base snapshot of a PR
2. scans the base snapshot
3. checks out the PR snapshot
4. scans the PR snapshot
5. compares the two
6. produces markdown and JSON reports
7. comments on the PR
8. fails the workflow if blocking findings are introduced

Why this matters:

- it extends the product into the software development lifecycle
- it shows the project can be used before deployment, not only after deployment
- it turns security findings into review-time feedback

What to say:

"An important architectural piece is the GitHub Actions pipeline. I did not want security to exist only in the web UI after a scan. The repository also includes a PR workflow that scans both the base and proposed code, normalizes results, compares them, and can block the pull request when new high-severity issues are introduced."

### 1. Frontend: Next.js Application

Relevant code:

- `frontend/app/page.tsx`
- `frontend/components/HomePage.tsx`
- `frontend/components/InputSection.tsx`
- `frontend/components/FindingsChatDrawer.tsx`

Why this layer exists:

- collect user input
- display progress and findings
- make the project usable for non-expert users

Why Next.js makes sense here:

- strong React ecosystem
- clean routing for pages like `/scans/[id]` and `/scans/[id]/chat`
- easy componentization

Architectural reason:

- the UI should be separate from scanner execution logic
- that separation keeps the backend focused on security operations and the frontend focused on presentation

What to say:

"I kept the frontend focused on workflow and visibility. The user can start a scan, watch it progress, review findings, and ask follow-up questions. The frontend does not perform security analysis itself; it is a client for the scanning platform."

### 2. Backend: FastAPI Service

Relevant code:

- `backend/app/main.py`
- `backend/app/routers/scans.py`
- `backend/app/routers/findings.py`
- `backend/app/routers/chat.py`

Why FastAPI makes sense:

- good support for async I/O
- clean API routing
- built-in validation through Pydantic
- natural fit for WebSocket endpoints and streaming responses

Architectural reason:

- this project performs network-heavy tasks
- async support matters because scanning involves many outbound requests

What to say:

"I chose FastAPI because the system is I/O-heavy rather than CPU-heavy. The application needs to manage many network operations, background tasks, and real-time communication, and FastAPI fits that model well."

### 3. Database Layer: SQLAlchemy and SQLite

Relevant code:

- `backend/app/database.py`
- `backend/app/models.py`

Why persistence matters:

- scans need to survive page refreshes
- findings need to be queryable after completion
- chat history needs to remain attached to a scan

Why this model is useful:

- `Scan` stores lifecycle state
- `Finding` stores detailed scan results
- `ChatMessage` stores conversation history

Why SQLite is understandable here:

- low setup overhead
- good for local development and demos
- enough for a single-node prototype

Tradeoff:

- not ideal for high concurrency or multi-tenant production scale

What to say:

"I used a simple relational model because the domain is naturally relational: one scan has many findings and many chat messages. SQLite keeps the prototype lightweight, while SQLAlchemy gives me a path to move to a larger database later without rewriting the whole data model."

### 4. Modular Scanner Architecture

Relevant code:

- `backend/app/scanner/base.py`
- `backend/app/services/scan_orchestrator.py`
- scanner modules under `backend/app/scanner/`

This is one of the strongest architectural decisions in the project.

Why:

- every OWASP area gets its own scanner module
- each module has the same interface: `scan() -> list[FindingData]`
- each module inherits shared helper behavior from `BaseScannerModule`

Benefits:

- easy to add a new scanner
- easier testing
- less duplication
- clearer ownership of logic

This is the classic benefit of abstraction:

- shared behavior in the base class
- specialized behavior in subclasses

What to say:

"I intentionally modeled each OWASP category as a separate module. That keeps the code easier to reason about and makes the system extensible. If I want to add another category later, I can implement a new scanner class without rewriting the orchestration layer."

### 5. Scan Orchestration as a Separate Service

Relevant code:

- `backend/app/services/scan_orchestrator.py`

Why not put scan logic directly inside the route?

- route handlers should stay small
- long-running work should be separated from HTTP request handling
- orchestration logic is easier to test and evolve when isolated

The orchestrator is responsible for:

- marking state transitions
- running modules
- updating progress
- collecting findings
- handling timeouts
- broadcasting completion or failure

This is a strong separation-of-concerns decision.

What to say:

"I kept the API layer thin and moved long-running scan coordination into a service. That separation reduces route complexity and makes the flow of a scan easier to maintain."

### 6. Real-Time Progress: WebSockets

Relevant code:

- `backend/app/websocket/scan_progress.py`
- `backend/app/main.py`
- `frontend/components/HomePage.tsx`

Why WebSockets were chosen:

- progress updates are event-driven
- the frontend should not have to constantly poll when real-time updates are available

Nice design detail:

- the frontend includes a polling fallback if the WebSocket fails

Why that matters:

- graceful degradation
- better resilience

What to say:

"I used WebSockets for real-time scan progress because a long-running scan should feel live to the user. I also added polling fallback in the frontend so the experience still works if the socket path fails."

### 7. Streaming Chat Responses: SSE-Like Pattern Over HTTP

Relevant code:

- `backend/app/routers/chat.py`
- `backend/app/services/chat_service.py`
- `frontend/lib/api.ts`

Why chat is separate from scanning:

- scanning is the detection phase
- chat is the explanation phase

This separation is important architecturally because:

- it keeps AI concerns from being mixed directly into the scanner engine
- it allows the AI to use findings as context after the scan is complete

What to say:

"I separated detection from explanation. The scanner discovers findings first, and the chat service then explains those findings using stored scan context. That keeps the system modular and reduces coupling between the scanning engine and the AI layer."

## Trust Boundaries

A product security manager will like it if you explicitly mention trust boundaries.

Here are the important ones:

1. User input boundary
2. Backend-to-target boundary
3. Backend-to-database boundary
4. Backend-to-LLM-provider boundary
5. Backend-to-frontend update boundary

Explain them like this:

"A user submits a target URL, which crosses the first trust boundary into the backend. The backend then crosses another trust boundary when it makes outbound requests to the target application. Findings are persisted internally in the database, and later some of that data is sent to the external AI provider to generate explanations. Real-time progress and results are finally exposed back to the frontend."

That answer sounds mature because it shows you think in systems, not just endpoints.

## Why Sequential Orchestration Was a Reasonable Choice

A manager may ask why all modules are not parallelized.

Strong answer:

"I chose sequential orchestration because it simplifies progress reporting, reduces coordination complexity, and lowers the risk of overwhelming a target system. The tradeoff is speed. To balance that, I used concurrency inside modules where checks are independent."

That is a very solid tradeoff explanation.

## Why This Architecture Is Good for a Prototype

Say:

"For a prototype or demo system, this architecture gives a strong balance of speed of development, clarity, and extensibility. It is simple enough to understand, but modular enough that individual parts can be hardened or replaced later. That includes both the runtime application and the GitHub Actions security workflow."

## Where the Architecture Would Need to Improve for Production

Be honest.

Major future improvements:

1. Add authentication and authorization
2. Replace SQLite with a production database
3. Add a queue or worker system for scans
4. Add rate limiting and tenant isolation
5. Add stronger outbound request controls and network sandboxing
6. Add secure secret management and encrypted evidence storage

What to say:

"I think the architecture is strong for a prototype, especially in terms of modularity. For production, the next step would be operational hardening: stronger isolation, authentication, queue-based execution, and tighter control over network and data exposure."

## A Strong 90-Second Version of This Entire Section

Say this:

"Architecturally, I separated the system into a frontend experience layer, a FastAPI backend, a persistence layer, a modular scanner engine, and an AI explanation layer. I chose that separation so each part has one main job: the frontend handles workflow, the backend handles APIs and orchestration, scanner modules handle detection logic, the database stores durable state, and the chat service explains findings after the fact. I used WebSockets for live progress, database persistence for continuity, and a base scanner abstraction so the system is easier to extend. The biggest tradeoff is that the current architecture is optimized for clarity and prototype velocity, not full production hardening."
