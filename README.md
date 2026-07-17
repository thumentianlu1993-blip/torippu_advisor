# Travel Planner MVP

A web application that automates travel research and produces an "oversaturated candidate report" for users and their travel companions to vote on, before producing a final travel guide.

## Stack

- **Frontend**: Next.js 14 (App Router), Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, SQLAlchemy, Celery, PostgreSQL, Redis
- **LLM**: 硅基流动 OpenAI-compatible API
- **Deployment**: Docker Compose + Nginx reverse proxy on an existing server

## Quick Start (local)

1. Copy environment variables:
   ```bash
   cp .env.example .env
   # edit .env with your keys
   ```

2. Build and start all services:
   ```bash
   docker compose up --build
   ```

3. Open the app:
   - Frontend: http://localhost:3000
   - Backend API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/healthz

## Project Structure

```
.
├── frontend/          # Next.js application
├── backend/           # FastAPI application
├── docker-compose.yml
├── docker-compose.prod.yml
├── nginx/
└── .env.example
```

## Development Notes

- The backend uses Celery workers for asynchronous data collection and report generation.
- PostgreSQL and Redis run in dedicated Docker Compose services.
- See individual `frontend/README.md` and `backend/README.md` for service-level details.
