from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models import Base, UserSettings
from config import POSTGRES_URL

engine = create_async_engine(POSTGRES_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_setting(user_id: int, key, value):
    async with async_session() as session:
        settings = await session.get(UserSettings, user_id)
        setattr(settings, key, value)
        # print(await settings.to_dict())
        await session.commit()


async def get_user_settings(user_id: int) -> UserSettings:
    async with async_session() as session:
        settings = await session.get(UserSettings, user_id)
        if not settings:
            settings = await create_user_settings(user_id)
        return settings


async def create_user_settings(user_id: int):
    async with async_session() as session:
        settings = UserSettings(user_id=user_id, chat_id=user_id)
        session.add(settings)
        await session.commit()
        return settings


async def delete_user(user_id):
    try:
        async with async_session() as session:
            s = await session.get(UserSettings, user_id)
            await session.delete(s)
            await session.commit()
    except Exception as e:
        print(e)
        return
