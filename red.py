from redis.asyncio import Redis
from models import UserSettings

redis = Redis(host='localhost', port=6379, db=0, decode_responses=True)


async def update_hsettings(user_id, key, value):
    k = f"user:{user_id}:settings"
    await redis.hset(k, key, value)
    await redis.expire(k, 300)


async def add_hsettings(user: UserSettings):
    k = f"user:{user.user_id}:settings"
    s = await user.to_dict()
    await redis.hset(k, mapping={k: '' if v is None else v if v.__class__ != bool else '1' if v else '0' for k, v in s.items()})
    await redis.expire(k, 300)


async def chek_hsettings(user_id) -> bool:
    k = f"user:{user_id}:settings"
    if await redis.exists(k) > 0:
        await redis.expire(k, 300)
        return True
    return False


async def get_hsettings(user_id: int) -> dict[str, int | str | float] | None:
    k = f"user:{user_id}:settings"
    if await chek_hsettings(user_id):
        result = await convert_from_redis(await redis.hgetall(k))
        # print(r)
        await redis.expire(k, 300)
        return result
    return None


async def convert_from_redis(s: dict) -> dict[str, int | str | float]:
    return {k: int(v) if v.isdigit() else float(v) if all(list(map(lambda x: x.isdigit(), v.split('.')))) else v for k, v in s.items()}