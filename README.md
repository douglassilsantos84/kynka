# Kynka

> Modular platform for AI agents, automation and intelligent business operations.

Kynka is an experimental software platform developed to explore the architecture and implementation of modular AI agents capable of interacting with business processes, tools, data and external services.

The project is being developed incrementally as a practical software engineering and artificial intelligence project.

## Current Status

**Active development — Kynka 6.0**

The current version includes a modular Python core, HTTP API, session management, contextual memory, intent routing, planning, plugin-based capabilities, inventory operations and demand management.

## Main Features

- Modular agent architecture
- HTTP REST API with FastAPI
- Isolated user sessions
- Contextual execution memory
- Intent routing
- Hybrid planning and execution
- Capability and plugin system
- General assistant fallback
- Inventory management
- Inventory movements
- Demand management
- Quantity-map importing
- Missing-material analysis
- SQLite persistence
- Local LLM integration through Ollama

## Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- SQLite
- Pytest

### AI

- Local LLM integration
- Ollama
- Intent routing
- Planning
- Context and memory
- Agent execution

### Engineering

- Git / GitHub
- REST APIs
- JSON
- Object-Oriented Programming
- Modular architecture
- Domain-driven organization
- Clean Architecture principles

## Architecture

Kynka is organized into distinct architectural layers:

```text
src/kynka/
│
├── domain/
│   ├── capabilities/
│   ├── demand/
│   ├── inventory/
│   ├── plugins/
│   └── providers/
│
├── application/
│   ├── agent/
│   ├── assistant/
│   ├── context/
│   ├── demand/
│   ├── inventory/
│   ├── intent_router/
│   ├── memory/
│   ├── planning/
│   └── recovery/
│
├── infrastructure/
│   ├── demand/
│   ├── importers/
│   ├── inventory/
│   └── providers/
│
├── kernel/
│
├── plugins/
│
└── presentation/
    ├── api/
    └── cli/
```

The goal of this structure is to keep business rules independent from infrastructure and presentation concerns while allowing new capabilities and integrations to evolve incrementally.

## API

The project exposes an HTTP API using FastAPI.

Main endpoints include:

```text
GET    /api/v1/health
GET    /api/v1/status

POST   /api/v1/sessions
DELETE /api/v1/sessions/{session_id}

POST   /api/v1/chat

GET    /api/v1/sessions/{session_id}/memory
DELETE /api/v1/sessions/{session_id}/memory

GET    /api/v1/sessions/{session_id}/variables

GET    /api/v1/capabilities
```

Additional inventory and demand endpoints are being developed as the business modules evolve.

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/douglassilsantos84/kynka.git
cd kynka
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements-api.txt
python -m pip install -e .
```

Alternatively, on Windows:

```powershell
.\FINALIZAR_BACKEND.ps1
```

### 4. Start the API

```powershell
python run_api.py
```

The API will be available locally.

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## Tests

Run the API test suite with:

```powershell
python -m pytest tests/api -q
```

## Configuration

Environment configuration is documented in:

```text
.env.example
```

Example:

```env
KYNKA_APP_NAME=Kynka API
KYNKA_VERSION=6.0.0
KYNKA_MODEL=llama3.2:3b
KYNKA_MEMORY_SIZE=100
KYNKA_SESSION_TTL_MINUTES=120
KYNKA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Real environment files are intentionally excluded from version control.

## Project Goals

Kynka is being built as a long-term platform rather than a single-purpose chatbot.

The development roadmap includes progressively expanding the platform with:

- business modules
- autonomous and proactive agent behavior
- external tool integrations
- voice interaction
- multimodal interfaces
- animated 2D/3D characters
- physical AI interfaces
- spatial and augmented-reality interaction

These capabilities will be introduced incrementally after stabilization of the core architecture and business modules.

## Why This Project Exists

Kynka is also a practical learning project focused on applying software engineering concepts to a real and continuously evolving codebase.

The project provides hands-on experience with:

- backend development
- API design
- software architecture
- AI agent design
- persistence
- testing
- version control
- refactoring
- incremental software development

## Author

**Douglas Santos**

Junior Software Developer focused on Python, backend development and Artificial Intelligence.

- GitHub: `douglassilsantos84`
- LinkedIn: `douglassilsantos`

---

Kynka is under active development. Architecture, APIs and features may change as the platform evolves.