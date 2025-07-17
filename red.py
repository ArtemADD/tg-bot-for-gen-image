from redis.asyncio import Redis
import db
from db_models import UserSettings, Models, Loras
from pd_schema import UserSchema, ModelSchema, LoraSchema
redis = Redis(host='localhost', port=6379, db=0, decode_responses=True)


async def check(k) -> bool:
    if await redis.exists(k) > 0:
        if 'user' in k:
            await redis.expire(k, 300)
        return True
    return False


async def check_user_loras(user_id):
    await check_h_loras()
    user_loras = await get_h_user(user_id, 'loras')
    h_loras = await get_h_loras('id')
    # print(user_loras, h_loras)
    for user_lora in user_loras:
        if user_lora not in h_loras:
            await update_h_user(user_id, 'loras', user_lora)


async def check_user_model(user_id):
    await check_h_models()
    user_model = await get_h_user(user_id, 'model_id')
    h_models = await get_h_models('id')
    # print(user_model, h_models)
    if user_model not in h_models:
        await update_h_user(user_id, 'model_id', None)


async def check_h_loras(lora: LoraSchema=None):
    if lora:
        db_loras = await db.get_all(Models)
        if lora in db_loras:
            return True
        return False
    if h_loras := await get_h_loras():
        db_loras = await db.get_all(Loras)
        for h_lora in h_loras:
            if h_lora not in db_loras:
                await del_h_lora(h_lora.id, h_only=True)
        for db_lora in db_loras:
            if db_lora not in h_loras:
                await add_h_lora(db_lora)
        return None
    await load_to_h_ml()
    return None


async def check_h_models(model: ModelSchema=None):
    if model:
        db_models = await db.get_all(Models)
        if model in db_models:
            return True
        return False
    if h_models := await get_h_models():
        db_models = await db.get_all(Models)
        for h_model in h_models:
            if h_model not in db_models:
                await del_h_lora(h_model.id, h_only=True)
        for db_model in db_models:
            if db_model not in h_models:
                await add_h_model(db_model)
        return None
    await load_to_h_ml()
    return None


async def check_exist_lm(pattern):
    cursor = 0
    checker = []
    while True:
        cursor, k = await redis.scan(cursor, match=pattern)
        checker.extend(k)
        if cursor == 0:
            break
    print(f'Check exists, pattern: {pattern}, find: {checker}')
    if checker:
        return True
    return False


async def clear_h_loras():
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match='loras:*')
        [await del_h_lora(int(key[6:]), h_only=True) for key in keys]
        if cursor == 0:
            break
    print('Clear Loras')


async def clear_h_models():
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match='models:*')
        [await del_h_model(int(key[7:]), h_only=True) for key in keys]
        if cursor == 0:
            break
    print('Clear Models')


async def load_to_h_ml():
    if not await get_h_loras():
        loras = await db.get_all(Loras)
        [await add_h_lora(lora) for lora in loras]
        # await redis.expire(loras_k, 600)
        print('Loaded Loras to Redis')
    if not await get_h_models():
        models = await db.get_all(Models)
        [await add_h_model(model) for model in models]
        # await redis.expire(models_k, 600)
        print('Loaded Models to Redis')


async def add_h_user(user: UserSchema):
    k = f"user:{user.id}:settings"
    # print(user)
    await redis.hset(k, mapping=user.model_dump())
    await redis.expire(k, 300)
    print(f'Added: {k}')


async def add_h_lora(lora: LoraSchema):
    k = f"loras:{lora.id}"
    # print(lora)
    await redis.hset(k, mapping=lora.model_dump())
    # await redis.expire(k, 600)
    print(f'Added: {k}')


async def add_h_model(model: ModelSchema):
    k = f"models:{model.id}"
    # print(model)
    await redis.hset(k, mapping=model.model_dump())
    # await redis.expire(k, 600)
    print(f'Added: {k}')


async def add_h_user_setting(user_id, key, value):
    k = f"user:{user_id}:settings"
    # print(f'{key}: {value}')
    await redis.hset(k, mapping={key: value})
    await redis.expire(k, 300)
    print(f'Added: {k}  {key}: {value}')


async def get_h_loras(key='') -> list[LoraSchema | str | int]:
    cursor = 0
    result = []
    while True:
        cursor, keys = await redis.scan(cursor, match='loras:*')
        res = [LoraSchema.model_validate(await redis.hgetall(k)) for k in keys]
        if key and type(key) == str:
            res = [getattr(r, key) for r in res]
        elif key:
            res = [[getattr(r, ks) for ks in key] for r in res]
        result.extend(res)
        if cursor == 0:
            break
    return result


async def get_h_models(key='') -> list[ModelSchema | str | int]:
    cursor = 0
    result = []
    while True:
        cursor, keys = await redis.scan(cursor, match='models:*')
        res = [ModelSchema.model_validate(await redis.hgetall(k)) for k in keys]
        if key:
            res = [getattr(r, key) for r in res]
        result.extend(res)
        if cursor == 0:
            break
    return result


async def get_h_user(user_id: int, key='') -> UserSchema | None | str | int | bool | list:
    k = f"user:{user_id}:settings"
    if await check(k):
        if key == 'page_loras':
            p = await redis.hget(k, key)
            return int(p) if p else None
        result = UserSchema.model_validate(await redis.hgetall(k))
        # print(result)
        if key:
            result = getattr(result, key)
        # print(result)
        await redis.expire(k, 300)
        return result
    return None


async def get_h_lora(lora_id: int) -> LoraSchema | None:
    k = f'loras:{lora_id}'
    if await check(k):
        result = LoraSchema.model_validate(await redis.hgetall(k))
        return result
    return None


async def get_h_model(model_id):
    k = f'models:{model_id}'
    if await check(k):
        result = ModelSchema.model_validate(await redis.hgetall(k))
        return result
    return None


async def update_h_user(user_id, key, value, h_only=False):
    try:
        if not h_only:
            await db.update_user(user_id, key, value)
        k = f"user:{user_id}:settings"
        if key == 'loras':
            user_loras = await get_h_user(user_id, 'loras')
            if value in user_loras:
                user_loras.remove(value)
            else:
                user_loras.append(value)
            value = ';'.join(list(map(lambda x: str(x), user_loras)))
        if type(value) == bool:
            if value:
                value = 1
            else:
                value = 0
        if value is None:
            value = ''
        await redis.hset(k, key, value)
        await redis.expire(k, 300)
    except Exception as e:
        raise e
        print(e.__repr__())


async def update_h_lora(lora_id, key, value, h_only=False):
    if not h_only:
        await db.update_lora(lora_id, key, value)
    k = f'loras:{lora_id}'
    await redis.hset(k, key, value)
    # await redis.expire(k, 600)


async def update_h_model(model_id, key, value, h_only=False):
    if not h_only:
        await db.update_model(model_id, key, value)
    k = f'models:{model_id}'
    await redis.hset(k, key, value)
    # await redis.expire(k, 600)


async def del_h_user_setting(user_id, key):
    k = f"user:{user_id}:settings"
    await redis.hdel(k, key)


async def del_h_user(user_id):
    k = f"user:{user_id}:settings"
    await redis.delete(k)
    print(f'Deleted User: {user_id}')


async def del_h_lora(lora_id, h_only=False):
    if not h_only:
        await db.del_lora(lora_id)
    k = f'loras:{lora_id}'
    await redis.delete(k)
    print(f'Deleted Lora: {lora_id}')


async def del_h_model(model_id, h_only=False):
    if not h_only:
        await db.get_model(model_id)
    k = f'models:{model_id}'
    await redis.delete(k)
    print(f'Deleted Model: {model_id}')
