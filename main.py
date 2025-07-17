import multiprocessing
from asyncio import run
import logging
from aiogram import Bot
from config import BOT_TOKEN
from db import init_db
from file_checker import start_check
from handlers import dp

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token=BOT_TOKEN)


async def main():
    await init_db()
    await start_check()
    await dp.start_polling(bot)


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    run(main())