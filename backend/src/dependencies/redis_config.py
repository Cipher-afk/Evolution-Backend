from redis.asyncio import Redis
from config import settings as s

redis_client = Redis(host=s.REDIS_HOST, port=s.REDIS_PORT,password=s.REDIS_PASSWORD, decode_responses=True)


async def add_to_blacklist(jti):
    await redis_client.set(jti, "")


async def is_in_blacklist(jti):
    return True if await redis_client.get(jti) is not None else False
