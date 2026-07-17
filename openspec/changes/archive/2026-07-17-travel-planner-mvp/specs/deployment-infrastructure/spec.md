## ADDED Requirements

### Requirement: Application runs in Docker Compose
The system SHALL provide a `docker-compose.yml` that launches the Next.js frontend, FastAPI backend, Celery worker, Celery beat, Redis, and PostgreSQL services.

#### Scenario: Developer runs docker compose up
- **WHEN** the developer runs `docker compose up`
- **THEN** all services start and the application is accessible on the configured ports

### Requirement: Backend exposes health check endpoint
The system SHALL provide a `/healthz` endpoint that returns HTTP 200 when the backend and database are healthy.

#### Scenario: Health check
- **WHEN** a request is made to `/healthz`
- **THEN** the backend returns 200 if the database connection is alive

### Requirement: Deployment coexists with existing project on same server
The system SHALL deploy alongside the existing `umafans.run` project without modifying the existing Docker Compose network unless necessary.

#### Scenario: New services start
- **WHEN** the new Docker Compose stack starts on the server
- **THEN** it does not bind host ports 80 or 443 and does not conflict with existing services

### Requirement: New project uses a separate subdomain
The system SHALL be served via a subdomain such as `travel.umafans.run` with DNS pointing to the same server.

#### Scenario: DNS configured
- **WHEN** the user configures the subdomain A record
- **THEN** requests to `travel.umafans.run` reach the server

### Requirement: Existing Nginx proxies to new backend
The system SHALL include an Nginx configuration snippet that adds a new server block for the subdomain, proxying to the new backend service port.

#### Scenario: Nginx reloaded
- **WHEN** the new Nginx configuration is applied and Nginx reloads
- **THEN** requests to `travel.umafans.run` are proxied to the new web service

### Requirement: PostgreSQL runs in a dedicated container
The system SHALL run a dedicated PostgreSQL container for the new project with persistent volume and separate database credentials.

#### Scenario: Database starts
- **WHEN** Docker Compose starts
- **THEN** a PostgreSQL container initialises the `travel` database and applies migrations

### Requirement: Environment variables configure external services
The system SHALL use environment variables for硅基流动 API key, Google Maps API key, Xiaohongshu credentials or third-party service tokens, and database connection strings.

#### Scenario: Deployment
- **WHEN** the application is deployed
- **THEN** sensitive credentials are loaded from `.env` or Docker secrets, not committed to Git

### Requirement: Static and media files are served correctly
The system SHALL serve frontend static assets and uploaded/downloaded media files without exposing the backend to direct traffic.

#### Scenario: User opens report page
- **WHEN** the user requests the report page
- **THEN** Nginx serves static files and proxies API requests to the backend
