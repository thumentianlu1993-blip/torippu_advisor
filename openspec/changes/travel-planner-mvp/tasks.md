## 1. Project Scaffold & Infrastructure

- [x] 1.1 Initialize Git repository and create top-level `README.md` with project overview and local dev instructions
- [x] 1.2 Create `docker-compose.yml` with services: frontend, backend, worker, beat, redis, postgres
- [x] 1.3 Create backend `Dockerfile` and `pyproject.toml` with FastAPI, SQLAlchemy, Celery, psycopg, httpx, python-dotenv
- [x] 1.4 Create frontend `package.json` and `Dockerfile` with Next.js 14 App Router, Tailwind CSS, shadcn/ui
- [x] 1.5 Create shared `.env.example` documenting all required environment variables
- [x] 1.6 Add `.gitignore` for Python, Node.js, Docker, and OS files
- [x] 1.7 Verify `docker compose up` starts all services without errors

## 2. Database Schema & Migrations

- [x] 2.1 Define SQLAlchemy models: Project, Report, Candidate, Vote, CollectionRun, Image
- [x] 2.2 Create Alembic migration setup and initial migration
- [x] 2.3 Add database health check endpoint `/healthz`
- [x] 2.4 Seed one example destination for manual testing (optional)

## 3. Backend Core APIs

- [x] 3.1 Implement `POST /api/projects` to create a project with validation
- [x] 3.2 Implement `GET /api/projects/{id}` and `GET /api/projects/by-token/{token}`
- [x] 3.3 Implement project status endpoint `GET /api/projects/{id}/status`
- [x] 3.4 Implement candidate listing endpoint `GET /api/projects/{id}/candidates` with filters
- [x] 3.5 Implement candidate manual edit endpoints (tier change, add, delete)
- [x] 3.6 Implement re-collection trigger `POST /api/projects/{id}/recollect`
- [x] 3.7 Add CORS and request/response logging middleware

## 4. Data Collection Pipeline

- [x] 4.1 Design abstract collector interface and registry
- [x] 4.2 Implement Google Maps Places collector using official API
- [x] 4.3 Implement Tripadvisor collector (API or page parsing)
- [x] 4.4 Implement Booking/Agoda accommodation collector
- [x] 4.5 Implement generic official website parser for ticket/hours info
- [x] 4.6 Research and integrate Xiaohongshu third-party collection service/tool
- [x] 4.7 Implement broad search strategy to discover candidate destinations/POIs
- [x] 4.8 Implement detailed search strategy per candidate
- [x] 4.9 Add collection result recording with source status and error logging
- [x] 4.10 Wire collection pipeline to Celery task triggered on project creation

## 5. Report Generation

- [x] 5.1 Design report JSON schema and persistence layer
- [x] 5.2 Implement LLM client for 硅基流动 API with structured JSON output
- [x] 5.3 Implement candidate classification into 7 important-experience categories
- [x] 5.4 Implement review summarization (positive/negative/pitfalls/Chinese focus)
- [x] 5.5 Implement core experience identification
- [x] 5.6 Implement food candidate splitting into reservation vs random pools
- [x] 5.7 Implement lodging area recommendation with multi-tier options
- [x] 5.8 Implement transport feasibility notes generator
- [x] 5.9 Implement budget estimation aggregator
- [x] 5.10 Implement travel tips generator (pre-trip and during-trip)
- [x] 5.11 Implement reference route generator (main/short/comfortable/premium)
- [x] 5.12 Wire report generation Celery task after collection completes
- [x] 5.13 Add report generation progress tracking and SSE or polling endpoint

## 6. Frontend UI

- [x] 6.1 Build project creation form page (`/`)
- [x] 6.2 Build project report page (`/p/{token}`)
- [x] 6.3 Build candidate card components with image, rating, summary, source badges
- [x] 6.4 Build report section navigation (core, important, food, lodging, transport, budget, tips, routes)
- [x] 6.5 Implement candidate filtering by category, tier, area, price
- [x] 6.6 Implement creator edit UI for tier changes, additions, deletions
- [x] 6.7 Implement voting buttons for visitors
- [x] 6.8 Implement creator toggle for hiding/revealing vote results
- [x] 6.9 Implement loading and error states for collection/report generation
- [x] 6.10 Implement responsive layout for mobile and desktop

## 7. Export Features

- [x] 7.1 Implement Google Maps point export as JSON/KML
- [x] 7.2 Add "Export to Google Maps" button to report page
- [x] 7.3 Ensure exports reflect current tiers and votes

## 8. Deployment & Operations

- [x] 8.1 Create production `docker-compose.prod.yml` with image tags and restart policies
- [x] 8.2 Create Nginx server block configuration for `travel.umafans.run`
- [x] 8.3 Document DNS setup steps for subdomain
- [x] 8.4 Document deployment steps: clone, env, docker compose up, nginx reload
- [x] 8.5 Test deployment on the server with a temporary port/domain if possible (local Docker Compose verified)
- [x] 8.6 Add basic logging and error tracking configuration

## 9. Testing & Validation

- [x] 9.1 Write backend unit tests for project creation and candidate CRUD
- [x] 9.2 Write backend tests for collection result recording and degradation logic
- [x] 9.3 Manually test report generation for one destination end-to-end
- [x] 9.4 Manually test Google Maps point export
- [x] 9.5 Manually test voting flow from an incognito browser
- [x] 9.6 Review and update `.env.example` and deployment docs based on testing

## 10. Final Review & Handoff

- [ ] 10.1 Run `/plan-eng-review` on proposal/design/specs/tasks
- [ ] 10.2 Address review findings
- [ ] 10.3 Run `/opsx:apply` to implement tasks incrementally
- [ ] 10.4 Run `/review` on final code
- [ ] 10.5 Run `/opsx:archive` to close the change
