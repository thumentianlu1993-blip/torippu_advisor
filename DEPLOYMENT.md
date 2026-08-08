# Deployment Guide

## Prerequisites

- Existing server running the `umafans.run` project on ports 80/443 with Nginx.
- Docker and Docker Compose installed.
- Domain `travel.umafans.run` DNS A record pointing to the server IP.

## DNS

Add an A record for `travel.umafans.run` pointing to the server IP. Wait for propagation.

## Server Setup

1. Clone the repository to a new directory (do not overwrite the existing project):
   ```bash
   git clone <repo-url> /opt/travel-planner
   cd /opt/travel-planner
   ```

2. Copy and edit environment variables:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Fill in all required keys, especially:
   - `SILICONFLOW_API_KEY`
   - `GOOGLE_MAPS_API_KEY`
   - Any optional collector keys you want to enable (see `docs/API_KEYS.md`;
     missing keys degrade gracefully per collector)
   - `DATABASE_URL` pointing to the `postgres` service
   - `NEXT_PUBLIC_API_URL=https://travel.umafans.run`
   - `CORS_ORIGINS=https://travel.umafans.run`
   - `TRUSTED_PROXY_CIDRS` set only to the actual reverse-proxy networks
   - `RATE_LIMIT_REDIS_URL=redis://redis:6379/1`

3. Build and start the production stack:
   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```

4. Do not start the production stack until the reviewed migration preflight,
   backup restore point, bridge artifact and explicit release authorization are
   recorded. The container runs `alembic upgrade head`; inspect first:
   ```bash
   docker compose -f docker-compose.prod.yml exec backend alembic current
   docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
   ```

5. Verify health:
   ```bash
   curl http://127.0.0.1:8000/healthz
   ```

## Nginx Configuration

1. Copy the provided server block:
   ```bash
   sudo cp nginx/travel.umafans.run.conf /etc/nginx/sites-available/travel.umafans.run
   sudo ln -s /etc/nginx/sites-available/travel.umafans.run /etc/nginx/sites-enabled/
   ```

2. Test and reload Nginx:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

3. (Recommended) Obtain HTTPS certificates with Certbot:
   ```bash
   sudo certbot --nginx -d travel.umafans.run
   ```

## Rollback

After the expand migration, only the reviewed bridge artifact is schema
compatible. It permits reads and fails closed for creator, collection, voting
and candidate writes. The pre-expand image is not a valid rollback target.

If something goes wrong:
```bash
cd /opt/travel-planner
docker compose -f docker-compose.prod.yml down
sudo rm /etc/nginx/sites-enabled/travel.umafans.run
sudo systemctl reload nginx
```

The existing `umafans.run` project remains untouched.
