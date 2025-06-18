import multiprocessing
import asyncio
import logging
import time
from io import BytesIO
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from db import init_db, save_setting, get_user_settings, get_img  # , delete_user
from ai import gen_img, init
from config import BOT_TOKEN, ADMIN_ID, BOT_ID
# from random_img import get_random_settings
from red import update_h, get_h, chek_h, add_h, get_ah

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token=BOT_TOKEN)
# Диспетчер
dp = Dispatcher()

processes = {}
statuses = {}
queues = {}

class SettingsStates(StatesGroup):
    waiting_for_prompt = State()


def generate_image(settings, queue):
    pipe = init()
    print(settings)
    try:
        for _ in range(settings['num_images']):
            response = {}
            image, seed = gen_img(pipe, **settings)
            time.sleep(2)
            bio = BytesIO()
            image.save(bio, format='PNG')
            bio.seek(0)
            doc = types.BufferedInputFile(bio.getvalue(), filename=f'gen_img{seed}.png')
            response['img'] = doc
            queue.put(response)
    except Exception as e:
        print(e)
        queue.put({'error': e})


async def check_user(msg: types.Message):
    user_id = msg.from_user.id
    chat_id= msg.chat.id
    if user_id == int(BOT_ID):
        user_id = chat_id
    if not await chek_h(user_id):
        settings = await get_user_settings(user_id)
        await add_h(settings)


def shorten(text, max_len=25):
    return text[:max_len] + "..." if text and len(text) > max_len else (text or "не задано")


async def show_menu(message: types.Message, s=False):
    kb = [
        # [types.InlineKeyboardButton(text="🎲 Рандом", callback_data='random')],
        [types.InlineKeyboardButton(text="🎨 Сгенерировать", callback_data='generate')],
        [types.InlineKeyboardButton(text="️⚙️ Настройки", callback_data='show_settings')]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    if s:
        await message.answer("Главное меню:", reply_markup=keyboard)
    else:
        await message.edit_text("Главное меню:", reply_markup=keyboard)


async def get_set_keyboard(user_id):
    s = await get_h(user_id)
    kb = [
        [types.InlineKeyboardButton(
            text=f"Промпт: {shorten(s['prompt']) if s['prompt'] else 'Не задан'}",
            callback_data='prompt')],
        [types.InlineKeyboardButton(
            text=f"Негативный промпт: {shorten(s['negative_prompt']) if s['prompt'] else 'Не задан'}",
            callback_data='negative_prompt')],
        [types.InlineKeyboardButton(
            text=f"Разрешение: {s['width']}x{s['height']}",
            callback_data='resolution')],
        [types.InlineKeyboardButton(
            text=f"Кол-во изображений: {s['num_images']}",
            callback_data='num_images')],
        [types.InlineKeyboardButton(
            text=f"Шагов: {s['steps']}",
            callback_data='steps')],
        [types.InlineKeyboardButton(
            text=f"Сид: {s['seed'] if s['seed'] != '' else 'рандом'}",
            callback_data='seed')],
        [types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data='back')]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)


# Handler на команду /start
@dp.message(CommandStart())
async def start(message: types.Message):
    await check_user(message)
    await show_menu(message, s=True)


@dp.callback_query(F.data == 'show_settings')
async def show_settings(callback: types.CallbackQuery):
    await check_user(callback.message)
    kb = await get_set_keyboard(callback.from_user.id)
    await callback.message.edit_text("Главное меню:", reply_markup=kb)


@dp.callback_query(F.data == 'back')
async def back_to_menu(callback: types.CallbackQuery):
    await check_user(callback.message)
    await show_menu(callback.message)


@dp.callback_query(F.data.in_({'prompt', 'negative_prompt', 'resolution', 'num_images', 'steps', 'seed', 'keep_current', 'reset_pipeline'}))
async def choice_settings(callback: types.CallbackQuery, state: FSMContext):
    await check_user(callback.message)
    msg = callback.message

    if callback.data == 'keep_current':
        await show_settings(callback)
        return

    user_id = callback.from_user.id
    s = await get_h(user_id)
    prompts = {
        'prompt': s['prompt'] if s['prompt'] else 'Введите новый промпт:',
        'negative_prompt': s['negative_prompt'] if s['negative_prompt'] else 'Введите негативный промпт:',
        'resolution': "Введите разрешение (например 1280x1280):",
        'num_images': "Сколько изображений сгенерировать?",
        'steps': "Введите количество шагов (num_inference_steps):",
        'seed': "Введите сид (или введите букву для random сида):"
    }
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="🚫 Оставить без изменений",
            callback_data="keep_current")],
    ])
    msg = await msg.edit_text(prompts[callback.data], reply_markup=keyboard)
    await state.update_data(setting=callback.data, msg=msg)
    await state.set_state(SettingsStates.waiting_for_prompt)


@dp.message(SettingsStates.waiting_for_prompt)
async def set_setting(message: types.Message, state: FSMContext):
    await check_user(message)
    callback = await state.get_data()
    setting = callback.get('setting')
    msg: types.Message = callback.get('msg')
    text = message.text
    user_id = message.from_user.id
    try:
        # Сохраняем в БД
        if setting == 'resolution':
            width, height = map(int, text.lower().split('x'))
            await update_h(user_id, 'width', width)
            await update_h(user_id,'height', height)
            await save_setting(user_id, 'width', width)
            await save_setting(user_id, 'height', height)
        elif setting == 'num_images':
            await update_h(user_id,'num_images', int(text))
            await save_setting(user_id, setting, int(text))
        elif setting == 'steps':
            await update_h(user_id,'steps', int(text))
            await save_setting(user_id, setting, int(text))
        elif setting == 'seed':
            await update_h(user_id,'seed', int(text) if text.isdigit() else '')
            await save_setting(user_id, setting, int(text) if text.isdigit() else None)
        else:
            await update_h(user_id,setting, text)
            await save_setting(user_id, setting, text)
        # Обновляем меню настроек
        if setting in ['prompt', 'negative_prompt']:
            await msg.edit_text(msg.text)
        else:
            await msg.delete()
        kb = await get_set_keyboard(user_id)
        await message.answer("Настройка обновлена.", reply_markup=kb)
        await state.clear()
    except Exception as e:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="🚫 Оставить без изменений",
                callback_data="keep_current")],
        ])
        await message.delete()
        await msg.edit_text(f"Ошибка ввода. Попробуйте снова.\n{e}", reply_markup=keyboard)


@dp.callback_query(F.data == 'stop_gen')
async def stop_gen(callback: types.CallbackQuery):
    await check_user(callback.message)
    chat_id = callback.message.chat.id
    if chat_id in processes.keys():
        proc = processes.get(chat_id)
        if proc.is_alive():
            proc.terminate()
            proc.join()
            # print('cancelled')
            statuses[chat_id] = 'cancelled'
            processes.pop(chat_id, None)
            queues.pop(chat_id, None)
            await callback.message.delete()
            await show_menu(callback.message, s=True)
    else:
        await callback.message.delete()
        await show_menu(callback.message, s=True)


@dp.callback_query(F.data == 'generate')
async def generate(callback: CallbackQuery):
    await check_user(callback.message)
    user_id = callback.from_user.id
    s = await get_h(user_id)
    if s['prompt'] == '' or s['negative_prompt'] == '':
        await callback.message.edit_text('Введите промпт или негативный промпт')
        await asyncio.sleep(3)
        await show_menu(callback.message)
    elif not list(processes.keys()):
        msg = callback.message
        chat_id = callback.message.chat.id
        q = multiprocessing.Queue(1)
        pr = multiprocessing.Process(target=generate_image, args=(s, q,), daemon=True)
        pr.start()
        processes[chat_id] = pr
        statuses[chat_id] = 'pending'
        queues[chat_id] = q
        asyncio.create_task(monitor_generation(chat_id, user_id, msg))
    else:
        await callback.message.edit_text('Извини, уже занят')
        await asyncio.sleep(5)
        await show_menu(callback.message)


async def monitor_generation(chat_id, user_id, msg):
    s = await get_h(user_id)
    n = s['num_images']
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="🚫 Остановить генерацию",
            callback_data="stop_gen")],
    ])
    try:
        for _ in range(n):
            await msg.edit_text(f'🎨 Генерация изображений {_ + 1}/{n}...', reply_markup=kb)
            while chat_id in processes.keys():
                # await msg.edit_text(f'🎨 Генерация изображений {_ + 1}/{n}{loading[0]}', reply_markup=kb)
                # loading = loading[1:] + loading[:1]
                if not queues.get(chat_id).empty():
                    break
                await asyncio.sleep(2)
            if statuses.get(user_id) == "cancelled":
                statuses.pop(chat_id, None)
                print('zxc')
                return
            queue = queues.get(chat_id)
            result = queue.get()
            # print(result)
            if 'error' in result.keys():
                raise result['error']
            h = await msg.answer_document(document=result['img'])
            await update_h(user_id, 'last_img', h.message_id)
            await save_setting(user_id, 'last_img', h.message_id)
    except Exception as e:
        print(e)
        await msg.edit_text(f'{e}')
        await asyncio.sleep(6)
    processes[chat_id].terminate()
    processes.pop(chat_id, None)
    queues.pop(chat_id, None)
    statuses.pop(chat_id, None)
    await msg.delete()
    await show_menu(msg, s=True)


@dp.message(Command('admin'))
async def admin(message: types.Message):
    user_id = message.from_user.id
    if user_id == int(ADMIN_ID):
        await check_user(message)
        keys = ['prompt', 'negative_prompt', 'width', 'height', 'num_images', 'steps', 'seed', 'chat_id', 'last_img']
        s = await get_ah()
        resp = '{\n' + '\n'.join([f'    {u}:\n{'        {\n' + '\n'.join([f'            {k}: {"None" if v == '' else v if str(v).isdigit() else f'"{v}"'};' for k, v in s.items() if k in keys]) + '\n        }'}\n' for u, s in s.items()]) + '}'
        await message.answer(resp)


@dp.message(Command('hist'))
async def show_hist(message: types.Message):
    if message.from_user.id == int(ADMIN_ID):
        await check_user(message)
        arg = int(message.text.split()[1])
        chat_hist, img_hist = await get_img(arg)
        if img_hist is not None:
            await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=chat_hist,
                message_id=img_hist
            )
        else:
            await message.answer('Нет истории')


async def main():
    await init_db()
    # await delete_user('')
    await dp.start_polling(bot)


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    asyncio.run(main())