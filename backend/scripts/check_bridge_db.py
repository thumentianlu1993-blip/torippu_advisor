"""Exercise the read-only bridge against the currently configured schema."""

import asyncio
import sys

from httpx import ASGITransport, AsyncClient

from app.bridge_app import app


async def main(share_token: str) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://bridge.test"
    ) as client:
        response = await client.get(f"/api/projects/by-token/{share_token}")
        assert response.status_code == 200, response.text
        assert response.json()["destination"] == "Legacy"
        assert "id" not in response.json() and "project_id" not in response.json()
        status = await client.get(f"/api/projects/by-token/{share_token}/status")
        assert status.status_code == 200, status.text
        candidates = await client.get(f"/api/projects/by-token/{share_token}/candidates")
        assert candidates.status_code == 200 and len(candidates.json()) == 1, candidates.text
        creator = await client.get(f"/api/projects/by-token/{share_token}/creator-check")
        assert creator.json() == {
            "creator": False,
            "recovery_required": False,
            "bridge_read_only": True,
        }
        report = await client.get(f"/api/projects/by-token/{share_token}/report")
        assert report.status_code == 200
        assert report.json()["status"] == "pending"
        denied = await client.post(f"/api/projects/by-token/{share_token}", json={})
        assert denied.status_code == 503
        assert denied.json() == {"detail": "bridge_write_disabled"}


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
