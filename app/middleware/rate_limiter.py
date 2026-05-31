"""
Rate Limiter — Redis-based sliding window rate limiting.

Applies per-IP rate limits to specific endpoints to prevent
brute-force attacks and API abuse.

Usage in routes:
    from app.middleware.rate_limiter import rate_limit

    @router.post("/login")
    async def login(request: Request, _=Depends(rate_limit("login", 5, 60))):
        ...
"""
from fastapi import Request, HTTPException, status, Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError
from app.redis import get_redis
from app.utils.logging import get_logger
from typing import Callable

logger = get_logger(__name__)


def rate_limit(key_prefix: str, max_requests: int, window_seconds: int) -> Callable:
    """
    Creates a rate limiting dependency using Redis sliding window counters.

    Args:
        key_prefix: Identifies the rate limit bucket (e.g., "login", "signup")
        max_requests: Maximum allowed requests within the window
        window_seconds: Size of the time window in seconds

    Returns:
        A FastAPI dependency that raises 429 if the limit is exceeded
    """
    async def _rate_limit_check(
        request: Request,
        redis: Redis = Depends(get_redis),
    ) -> None:
        # Build key from prefix + client IP
        # Trust X-Forwarded-For if behind a proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
            
        redis_key = f"ratelimit:{key_prefix}:{client_ip}"

        try:
            # Increment the counter
            current_count = await redis.incr(redis_key)

            # Set TTL only on the first request (when count goes from 0 to 1)
            if current_count == 1:
                await redis.expire(redis_key, window_seconds)

            if current_count > max_requests:
                # Get remaining TTL for the Retry-After header
                ttl = await redis.ttl(redis_key)
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "ip": client_ip,
                        "endpoint": key_prefix,
                        "count": current_count,
                        "limit": max_requests,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Try again in {ttl} seconds.",
                    headers={"Retry-After": str(ttl)},
                )
        except RedisError as exc:
            logger.error("Redis error in rate limiter", extra={"error": str(exc)})
            # Fail open: if Redis is down, don't block requests
            # (Rate limiting is a nicety, not a security-critical gate)

    return _rate_limit_check
