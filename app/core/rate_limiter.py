# app/core/rate_limiter.py
import time
import logging
from typing import Optional, Tuple

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings  # suponho que já tenha settings.REDIS_URL

logger = logging.getLogger(__name__)

# use string content of lua or load from file
TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local data = redis.call("HMGET", key, "tokens", "last")
local tokens = tonumber(data[1]) or capacity
local last = tonumber(data[2]) or now

local delta = math.max(0, now - last)
local new_tokens = math.min(capacity, tokens + delta * refill_rate)

local allowed = 0
if new_tokens >= requested then
  allowed = 1
  new_tokens = new_tokens - requested
end

redis.call("HMSET", key, "tokens", tostring(new_tokens), "last", tostring(now))
local ttl = math.ceil((capacity / math.max(refill_rate,1e-9)) * 2)
redis.call("EXPIRE", key, ttl)
return {allowed, math.floor(new_tokens)}
"""

class RedisRateLimiter:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        self._sha: Optional[str] = None

    async def init(self):
        if not self.redis_url:
            logger.warning("REDIS_URL not configured; rate limiter disabled.")
            return
        self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        try:
            self._sha = await self._redis.script_load(TOKEN_BUCKET_LUA)
            logger.info("Rate limiter Lua script loaded (sha=%s)", self._sha)
        except RedisError:
            logger.exception("Failed to load rate limiter Lua script")
            self._sha = None

    async def allow_request(self, key: str, capacity: int, refill_per_sec: float, requested: int = 1) -> Tuple[bool, int]:
        """Return (allowed, remaining_tokens). On Redis failure -> deny-safe (False, 0)."""
        if not self._redis:
            # dev fallback: allow
            logger.debug("Redis not initialized, allowing request (dev fallback)")
            return True, capacity - requested

        now = time.time()
        try:
            if self._sha:
                res = await self._redis.evalsha(self._sha, 1, key, capacity, refill_per_sec, now, requested)
            else:
                res = await self._redis.eval(TOKEN_BUCKET_LUA, 1, key, capacity, refill_per_sec, now, requested)
            # res is table: [allowed, remaining]
            allowed = bool(int(res[0]))
            remaining = int(res[1])
            return allowed, remaining
        except Exception:
            logger.exception("Rate limiter redis error; denying request")
            return False, 0

    async def close(self):
        if self._redis:
            await self._redis.close()
            await self._redis.connection_pool.disconnect()
