import redis.asyncio as redis
from app.core.config import settings

class RedisClient:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    async def set_token(self, token: str, value: str, expire: int):
        await self.redis.set(f"token:{token}", value, ex=expire)

    async def get_token(self, token: str) -> str | None:
        return await self.redis.get(f"token:{token}")

    async def delete_token(self, token: str):
        await self.redis.delete(f"token:{token}")

    async def close(self):
        await self.redis.close()

redis_client = RedisClient()
