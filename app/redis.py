import redis.asyncio as redis
from app.config import settings

# Create an async redis client pool
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis():
    return redis_client
