from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from db_models import Base, UserSettings, Models, Loras
from pd_schema import UserSchema, ModelSchema, LoraSchema
from config import POSTGRES_URL

engine = create_async_engine(POSTGRES_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def update_user(user_id: int, key, value):
    # print(hasattr(UserSettings, key), key)
    if not hasattr(UserSettings, key):
        return
    async with async_session() as session:
        user = await session.get(UserSettings, user_id)
        if key == 'loras' and value is not None:
            lora = await session.get(Loras, value)
            if lora in user.loras:
                user.loras.remove(lora)
            else:
                user.loras.append(lora)
            # print(settings.loras)
        elif key == 'model_id' or key == 'model':
            user.model_id = value
            # print(settings.model)
        else:
            setattr(user, key, value)
        # print(await UserSchema.model_validate(settings))
        await session.commit()


async def update_model(model_id: int, key, value):
    async with async_session() as session:
        model = await session.get(Models, model_id)
        print(key, value)
        setattr(model, key, value)
        # print(await ModelSchema.model_validate(model))
        await session.commit()


async def update_lora(lora_id: int, key, value):
    async with async_session() as session:
        lora = await session.get(Loras, lora_id)
        setattr(lora, key, value)
        # print(await LoraSchema.model_validate(lora))
        await session.commit()


async def get_all(table: type[Models | UserSettings| Loras]) -> list[UserSchema | LoraSchema | ModelSchema]:
    async with async_session() as session:
        if table is UserSettings:
            schema = UserSchema
        elif table is Models:
            schema = ModelSchema
        elif table is Loras:
            schema = LoraSchema
        r = await session.execute(select(table))
        r = r.unique().scalars().all()
        if r:
            r = [schema.model_validate(i) for i in r]
    return r


async def get_user(user_id: int) -> UserSchema:
    async with async_session() as session:
        if user := await session.get(UserSettings, user_id):
            user = UserSchema.model_validate(user)
        else:
            user = await add_user(user_id)
        return user


async def get_model(model_id: int) -> ModelSchema | None:
    async with async_session() as session:
        if model := await session.get(Models, model_id):
            model = ModelSchema.model_validate(model)
            return model
        return None


async def get_lora(lora_id: int) -> LoraSchema | None:
    async with async_session() as session:
        if lora := await session.get(Loras, lora_id):
            lora = LoraSchema.model_validate(lora)
            return lora
        return None


async def add_user(user_id: int) -> UserSchema:
    async with async_session() as session:
        default_model = await get_all(Models)
        user = UserSettings(id=user_id, model_id=default_model[0].id if default_model else None, loras=[])
        session.add(user)
        await session.commit()
        return UserSchema.model_validate(user)


async def add_model(path, name, description='', t='') -> ModelSchema:
    async with async_session() as session:
        model = Models(name=name if len(name) < 12 else name[:12], path=path, description=description)
        session.add(model)
        await session.commit()
    return ModelSchema.model_validate(model)


async def add_lora(path, name, description='') -> LoraSchema:
    async with async_session() as session:
        lora = Loras(name=name if len(name) < 12 else name[:12], path=path, description=description)
        session.add(lora)
        await session.commit()
    return LoraSchema.model_validate(lora)


async def del_model(model_id):
    async with async_session() as session:
        model = await session.get(Models, model_id)
        await session.delete(model)
        await session.commit()


async def del_lora(lora_id):
    async with async_session() as session:
        lora = await session.get(Loras, lora_id)
        await session.delete(lora)
        await session.commit()


async def del_user(user_id):
    try:
        async with async_session() as session:
            s = await session.get(UserSettings, user_id)
            await session.delete(s)
            await session.commit()
    except Exception as e:
        print(e)
        return
