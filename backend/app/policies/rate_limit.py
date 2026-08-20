import hashlib
import time
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class RateLimitUnavailable(RuntimeError):
    pass


class RedisRateLimiter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def check(self, identity: str) -> RateLimitDecision:
        if self.settings.redis_url is None:
            raise RateLimitUnavailable
        digest = hashlib.sha256(identity.encode()).hexdigest()[:24]
        now = int(time.time())
        windows = (
            (60, self.settings.rate_limit_anonymous_per_minute),
            (3600, self.settings.rate_limit_anonymous_per_hour),
        )
        client = Redis.from_url(self.settings.redis_url.get_secret_value())
        try:
            for seconds, limit in windows:
                bucket = now // seconds
                key = f"rate:anonymous:{digest}:{seconds}:{bucket}"
                async with client.pipeline(transaction=True) as pipeline:
                    pipeline.incr(key)
                    pipeline.expire(key, seconds + 5, nx=True)
                    count, _ = await pipeline.execute()
                if int(count) > limit:
                    return RateLimitDecision(
                        allowed=False,
                        retry_after_seconds=seconds - (now % seconds),
                    )
        except Exception as error:
            raise RateLimitUnavailable from error
        finally:
            await client.aclose()
        return RateLimitDecision(allowed=True, retry_after_seconds=0)
