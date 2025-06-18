from redis.asyncio import Redis
from models import UserSettings

redis = Redis(host='localhost', port=6379, db=0, decode_responses=True)


async def update_h(user_id, key, value):
    k = f"user:{user_id}:settings"
    await redis.hset(k, key, value)


async def add_h(user: UserSettings):
    k = f"user:{user.user_id}:settings"
    s = await user.to_dict()
    await redis.hset(k, mapping={k: v if v is not None else '' for k, v in s.items()})


async def chek_h(user_id):
    k = f"user:{user_id}:settings"
    return await redis.exists(k) > 0


async def get_h(user_id: int):
    k = f"user:{user_id}:settings"
    if await chek_h(user_id):
        print(r := await go_int(await redis.hgetall(k)))
        return r
    return None


async def get_ah():
    cursor = 0
    user_settings = {}

    while True:
        cursor, keys = await redis.scan(cursor=cursor, match="user:*:settings", count=100)

        for key in keys:
            # Извлекаем user_id из ключа, например: "user:123:settings"
            parts = key.split(":")
            if len(parts) != 3:
                continue
            user_id = int(parts[1])

            settings = await redis.hgetall(key)
            user_settings[user_id] = settings

        if cursor == 0:
            break

    return user_settings


async def go_int(s: dict):
    return {k: v if not v.isdigit() else int(v) for k, v in s.items() }