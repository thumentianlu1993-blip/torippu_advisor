"""Abuse limits and trusted client address normalization.

The in-process fallback is deliberately fail-closed outside tests. Production
deployments use Redis atomic counters; database writes happen only after this
gateway returns.
"""

import secrets
import time
from ipaddress import IPv6Address, IPv6Network, ip_address, ip_network

from fastapi import HTTPException, Request

from app.config import settings

_ROLLING_WINDOW_LUA = """
local now = tonumber(ARGV[1])
local member = ARGV[2]
for i = 1, #KEYS do
  local window = tonumber(ARGV[2 + (i - 1) * 2 + 1])
  local limit = tonumber(ARGV[2 + (i - 1) * 2 + 2])
  redis.call('ZREMRANGEBYSCORE', KEYS[i], '-inf', now - window)
  if redis.call('ZCARD', KEYS[i]) >= limit then return 0 end
end
for i = 1, #KEYS do
  local window = tonumber(ARGV[2 + (i - 1) * 2 + 1])
  redis.call('ZADD', KEYS[i], now, member)
  redis.call('EXPIRE', KEYS[i], window)
end
return 1
"""

CREATE_HOURLY_LIMIT = 3
CREATE_DAILY_LIMIT = 10
RECOLLECT_HOURLY_LIMIT = 1
RECOLLECT_DAILY_LIMIT = 6
VOTE_TEN_MINUTE_LIMIT = 60
VOTE_DAILY_LIMIT = 300
VOTE_CHANGE_DAILY_LIMIT = 10
RECOVERY_HOURLY_LIMIT = 5


def trusted_client_ip(request: Request) -> str:
    peer = ip_address(request.client.host if request.client else "127.0.0.1")
    networks = [ip_network(c.strip()) for c in settings.TRUSTED_PROXY_CIDRS.split(",") if c.strip()]
    forwarded = request.headers.get("X-Forwarded-For", "")
    try:
        chain = [ip_address(item.strip()) for item in forwarded.split(",") if item.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_forwarded_chain") from exc
    if any(peer in network for network in networks) and forwarded:
        # Walk from the trusted peer toward the client. Anything further left
        # than the first untrusted hop is attacker-controlled and ignored.
        chain.append(peer)
        while len(chain) > 1 and any(chain[-1] in network for network in networks):
            chain.pop()
        value = chain[-1]
    else:
        value = peer
    if isinstance(value, IPv6Address):
        return str(IPv6Network((value, 64), strict=False).network_address) + "/64"
    return str(value)


async def _enforce(scope: str, key: str, limits: tuple[tuple[int, int], ...]) -> None:
    if settings.RATE_LIMIT_REDIS_URL:
        from redis.asyncio import from_url

        client = from_url(settings.RATE_LIMIT_REDIS_URL, decode_responses=True)
        keys = [f"travel:limit:{scope}:{window}:{key}" for window, _ in limits]
        arguments: list[str | int] = [int(time.time()), secrets.token_hex(12)]
        for window, limit in limits:
            arguments.extend((window, limit))
        try:
            allowed = await client.eval(_ROLLING_WINDOW_LUA, len(keys), *keys, *arguments)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="rate_limit_unavailable") from exc
        finally:
            await client.aclose()
        if not allowed:
            raise HTTPException(status_code=429, detail="rate_limit_exceeded")
        return
    if settings.DENY_EXTERNAL_NETWORK:
        return
    raise HTTPException(status_code=503, detail="rate_limit_unavailable")


async def enforce_project_create_limit(request: Request) -> None:
    await _enforce(
        "create",
        trusted_client_ip(request),
        ((3600, CREATE_HOURLY_LIMIT), (86400, CREATE_DAILY_LIMIT)),
    )


async def enforce_recollect_limit(request: Request, project_key: str) -> None:
    await _enforce(
        "recollect", project_key, ((3600, RECOLLECT_HOURLY_LIMIT), (86400, RECOLLECT_DAILY_LIMIT))
    )


async def enforce_vote_limit(request: Request, project_key: str, voter_key: str) -> None:
    ip = trusted_client_ip(request)
    await _enforce(
        "vote", f"{project_key}:{ip}", ((600, VOTE_TEN_MINUTE_LIMIT), (86400, VOTE_DAILY_LIMIT))
    )
    await _enforce("vote-change", f"{project_key}:{voter_key}", ((86400, VOTE_CHANGE_DAILY_LIMIT),))


async def enforce_recovery_limit(request: Request, project_key: str) -> None:
    await _enforce(
        "recovery",
        f"{project_key}:{trusted_client_ip(request)}",
        ((3600, RECOVERY_HOURLY_LIMIT),),
    )
