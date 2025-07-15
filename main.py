import multiprocessing
import asyncio
import logging
from io import BytesIO
from aiogram import Bot, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from db import init_db, save_setting, get_user_settings
from config import BOT_TOKEN, BOT_ID, MODELS, SCHEDULERS, LORAS, LORAS_COLUMNS, LORAS_ROWS
from red import update_hsettings, get_hsettings, chek_hsettings, add_hsettings, add_once_hsettings, del_once_hsettings
from keyboards import get_base_settings_menu, get_model_settings_menu, get_model_menu, get_scheduler_menu, get_lora_menu
from handlers import dp
# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token=BOT_TOKEN)


processes = {}
statuses = {}
queues = {}

class BaseSettingsStates(StatesGroup):
    waiting_for_prompt = State()


async def check_user(msg: Message) -> int:
    user_id = msg.from_user.id
    chat_id= msg.chat.id
    if user_id == int(BOT_ID):
        user_id = chat_id
    if not await chek_hsettings(user_id):
        settings = await get_user_settings(user_id)
        await add_hsettings(settings)
    return user_id


async def check_loras(user_id: int, loras: str) -> list[str] | str:
    if ';' in loras:
        loras = loras.split(';')
        if not all(list(map(lambda x: x in LORAS.keys(), loras))):
            loras = [lora for lora in loras if lora in LORAS.keys()]
            await update_hsettings(user_id, 'loras', ';'.join(loras))
            await save_setting(user_id, 'loras', ';'.join(loras))
    elif loras != '' and loras not in LORAS.keys():
        loras = ''
        await update_hsettings(user_id, 'loras', '')
        await save_setting(user_id, 'loras', '')
    return loras


# Handler на команду /start
@dp.message(CommandStart())
async def start(message: Message):
    await check_user(message)
    await show_base_settings(message, s=True)


async def show_base_settings(msg: Message, s=False):
    await check_user(msg)
    kb = await get_base_settings_menu(msg.chat.id)
    text_msg = '☰ Главное меню:'
    await msg.answer(text_msg, reply_markup=kb) if s else await msg.edit_text(text_msg, reply_markup=kb)


@dp.callback_query(F.data == 'model_settings')
async def model_settings(callback: CallbackQuery):
    await check_user(callback.message)
    if await get_hsettings(callback.message.chat.id, 'page_loras') is not None: await del_once_hsettings(callback.message.chat.id, 'page_loras')
    await show_model_settings(callback.message)


async def show_model_settings(msg: Message, s=False):
    keyboard = await get_model_settings_menu(msg.chat.id)
    text_msg = '⚙️ Настройки модели'
    await msg.answer(text_msg, reply_markup=keyboard) if s else await msg.edit_text(text_msg, reply_markup=keyboard)


@dp.callback_query(F.data == 'choice_model')
async def choice_model(callback: CallbackQuery):
    await check_user(callback.message)
    await show_model_menu(callback.message)


async def show_model_menu(msg: Message):
    keyboard, model = await get_model_menu(msg.chat.id)
    await msg.edit_text(f'🧠 Текущая модель: {model}', reply_markup=keyboard)


@dp.callback_query(F.data.in_(MODELS.keys()))
async def set_model(callback: CallbackQuery):
    await check_user(callback.message)
    await update_hsettings(callback.message.chat.id, 'model', callback.data)
    await save_setting(callback.message.chat.id, 'model', callback.data)
    await show_model_settings(callback.message)


@dp.callback_query(F.data == 'scheduler')
async def show_scheduler(callback: CallbackQuery):
    await check_user(callback.message)
    keyboard, scheduler = await get_scheduler_menu(callback.message.chat.id)
    await callback.message.edit_text(f'🧠 Выбор scheduler ({scheduler}):', reply_markup=keyboard)


@dp.callback_query(F.data.in_(SCHEDULERS))
async def set_scheduler(callback: CallbackQuery):
    await check_user(callback.message)
    await update_hsettings(callback.message.chat.id, 'scheduler', callback.data)
    await save_setting(callback.message.chat.id, 'scheduler', callback.data)
    await show_model_settings(callback.message)


@dp.callback_query(F.data == 'lora')
async def show_loras(callback: CallbackQuery):
    await check_user(callback.message)
    await show_loras_menu(callback.message)


async def show_loras_menu(msg: Message):
    loras = await check_loras(msg.chat.id, await get_hsettings(msg.chat.id,'loras'))
    p = await get_hsettings(msg.chat.id, 'page_loras')
    if len(LORAS_COLUMNS) > LORAS_ROWS and p is None:
        await add_once_hsettings(msg.chat.id, 'page_loras', 1)
        keyboard = await get_lora_menu(msg.chat.id, loras)
    else:
        keyboard = await get_lora_menu(msg.chat.id, loras)
    await msg.edit_text('🖼️ Выбор lora:', reply_markup=keyboard)


@dp.callback_query(F.data.in_(LORAS.keys()))
async def set_loras(callback: CallbackQuery):
    await check_user(callback.message)
    loras = await get_hsettings(callback.message.chat.id, 'loras')
    loras = loras.split(';') if ';' in loras else [] if loras == '' else [loras]
    loras.remove(callback.data) if callback.data in loras else loras.append(callback.data)
    loras = ';'.join(loras)
    await update_hsettings(callback.message.chat.id, 'loras', loras)
    await save_setting(callback.message.chat.id, 'loras', loras)
    await show_loras_menu(callback.message)


@dp.callback_query(F.data == 'back_lora')
async def back_lora(callback: CallbackQuery):
    await check_user(callback.message)
    p = await get_hsettings(callback.message.chat.id, 'page_loras')
    if p:
        await update_hsettings(callback.message.chat.id, 'page_loras', p - 1)
        await show_loras_menu(callback.message)
    else:
        await show_model_settings(callback.message)

@dp.callback_query(F.data == 'next_lora')
async def next_lora(callback: CallbackQuery):
    await check_user(callback.message)
    p = await get_hsettings(callback.message.chat.id, 'page_loras')
    if p:
        await update_hsettings(callback.message.chat.id, 'page_loras', p + 1)
        await show_loras_menu(callback.message)
    else:
        await show_model_settings(callback.message)


@dp.callback_query(F.data == 'cuda')
async def set_cuda(callback: CallbackQuery):
    await check_user(callback.message)
    cuda = await get_hsettings(callback.message.chat.id, 'cuda')
    await update_hsettings(callback.message.chat.id, 'cuda', abs(cuda - 1))
    await save_setting(callback.message.chat.id, 'cuda', True if cuda == 1 else False)
    await show_model_settings(callback.message)


@dp.callback_query(F.data == 'back')
async def back_to_menu(callback: CallbackQuery):
    await check_user(callback.message)
    await show_base_settings(callback.message)


@dp.callback_query(F.data.in_(['prompt', 'negative_prompt', 'resolution', 'num_images', 'steps', 'seed', 'keep_current', 'reset_pipeline', 'guidance_scale']))
async def choice_settings(callback: CallbackQuery, state: FSMContext):
    await check_user(callback.message)
    msg = callback.message

    if callback.data == 'keep_current':
        c = await state.get_data()
        setting = c.get('setting')
        await state.clear()
        if setting in ['prompt', 'negative_prompt', 'num_images']:
            await show_base_settings(msg)
        else:
            await show_model_settings(msg)
        return

    user_id = callback.from_user.id
    s = await get_hsettings(user_id)
    rule_settings = {
        'prompt': s['prompt'] if s['prompt'] else 'Введите новый промпт:',
        'negative_prompt': s['negative_prompt'] if s['negative_prompt'] else 'Введите негативный промпт:',
        'resolution': "Введите разрешение (например 1280x1280):",
        'num_images': "Сколько изображений сгенерировать?",
        'steps': "Введите количество шагов (num_inference_steps):",
        'guidance_scale': "Введите cfg:",
        'seed': "Введите сид (или введите букву для random сида):"
    }
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="🚫 Оставить без изменений",
            callback_data="keep_current")],
    ])
    msg = await msg.edit_text(rule_settings[callback.data], reply_markup=keyboard)
    await state.update_data(setting=callback.data, msg=msg)
    await state.set_state(BaseSettingsStates.waiting_for_prompt)


@dp.message(BaseSettingsStates.waiting_for_prompt)
async def set_setting(message: Message, state: FSMContext):
    await check_user(message)
    callback = await state.get_data()
    setting = callback.get('setting')
    msg: Message = callback.get('msg')
    await state.clear()
    text = message.text
    user_id = message.from_user.id
    try:
        # Сохраняем в БД
        if setting == 'resolution':
            width, height = map(int, text.lower().split('x'))
            await update_hsettings(user_id, 'width', width)
            await update_hsettings(user_id,'height', height)
            await save_setting(user_id, 'width', width)
            await save_setting(user_id, 'height', height)
        elif setting == 'num_images':
            await update_hsettings(user_id,'num_images', int(text))
            await save_setting(user_id, setting, int(text))
        elif setting == 'steps':
            await update_hsettings(user_id,'steps', int(text))
            await save_setting(user_id, setting, int(text))
        elif setting == 'seed':
            await update_hsettings(user_id,'seed', int(text) if text.isdigit() else '')
            await save_setting(user_id, setting, int(text) if text.isdigit() else None)
        elif setting == 'guidance_scale':
            await update_hsettings(user_id,'guidance_scale', float(text))
            await save_setting(user_id, setting, float(text))
        else:
            await update_hsettings(user_id,setting, text)
            await save_setting(user_id, setting, text)
        # Обновляем меню настроек
        if setting in ['prompt', 'negative_prompt']:
            await msg.edit_text(msg.text)
        else:
            await msg.delete()
        if setting in ['prompt', 'negative_prompt', 'num_images']:
            await show_base_settings(message, s=True)
        else:
            await show_model_settings(message, s=True)
    except Exception as e:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="🚫 Оставить без изменений",
                callback_data="keep_current")],
        ])
        await message.delete()
        await msg.edit_text(f"Ошибка ввода. Попробуйте снова.\n{e}", reply_markup=keyboard)


@dp.callback_query(F.data == 'stop_gen')
async def stop_gen(callback: CallbackQuery):
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
            await show_base_settings(callback.message, s=True)
    else:
        await callback.message.delete()
        await show_base_settings(callback.message, s=True)


@dp.callback_query(F.data == 'generate')
async def generate(callback: CallbackQuery):
    await check_user(callback.message)
    user_id = callback.from_user.id
    s = await get_hsettings(user_id)
    s['loras'] = await check_loras(user_id, s['loras'])
    # print(s['loras'])
    if s['prompt'] == '' or s['negative_prompt'] == '':
        await callback.message.edit_text('Введите промпт или негативный промпт')
        await asyncio.sleep(3)
        await show_base_settings(callback.message)
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
        await show_base_settings(callback.message)


def generate_image(settings, queue):
    try:
        loader = MODELS[settings['model']].copy()
        if settings['scheduler'] != 'None': loader.set_scheduler(settings['scheduler'])
        # print(settings['loras'])
        loader.set_cuda(settings['cuda'])
        loader.set_lora([LORAS[lora] for lora in settings['loras']] if settings['loras'].__class__ == list else LORAS[settings['loras']])
        loader()
        # print(f'{settings}\n{loader}')
        n = settings['num_images'] if settings['seed'] == '' else 1
        print(f'Generate prompt: {settings['prompt']}' if settings['seed'] == '' else f'Generate prompt: {settings['prompt']}\nSeed: {settings['seed']}')
        for _ in range(n):
            response = {}
            image, seed = loader.gen_img(**settings)
            bio = BytesIO()
            image.save(bio, format='PNG')
            bio.seek(0)
            doc = types.BufferedInputFile(bio.getvalue(), filename=f'img_{settings['model']}_{seed}.png')
            response['img'] = doc
            queue.put(response)
    except Exception as e:
        # raise e
        print(e)
        queue.put({'error': e})


async def monitor_generation(chat_id, user_id, msg):
    s = await get_hsettings(user_id)
    n = s['num_images'] if s['seed'] == '' else 1
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
            await check_user(msg)
            await update_hsettings(user_id, 'last_img', h.message_id)
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
    await show_base_settings(msg, s=True)


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    asyncio.run(main())