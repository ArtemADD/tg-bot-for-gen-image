from config import MODELS, SCHEDULERS, LORAS_COLUMNS, LORAS_ROWS
from red import get_hsettings
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def shorten(text, max_len=25):
    return text[:max_len] + "..." if text and len(text) > max_len else (text or "не задано")


async def get_base_settings_menu(user_id):
    settings = await get_hsettings(user_id)
    kb = [
        # [InlineKeyboardButton(text="🎨 Сгенерировать", callback_data='generate')],
        [InlineKeyboardButton(
            text=f"✨ Промпт: {shorten(settings['prompt']) if settings['prompt'] else 'Не задан'}",
            callback_data='prompt')],
        [InlineKeyboardButton(
            text=f"💥 Негативный промпт: {shorten(settings['negative_prompt']) if settings['prompt'] else 'Не задан'}",
            callback_data='negative_prompt')],
        [InlineKeyboardButton(
            text=f"🔢 Кол-во изображений: {settings['num_images'] if settings['seed'] == '' else 'Установлен сид'}",
            callback_data='num_images')],
        [InlineKeyboardButton(
            text="️⚙️ Настройки Модели",
            callback_data='model_settings')],
        [InlineKeyboardButton(text="🎨 Сгенерировать", callback_data='generate')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_model_settings_menu(user_id):
    settings  = await get_hsettings(user_id)
    kb = [
        [InlineKeyboardButton(text=f"🧠 Модель: {settings['model']}⠀", callback_data='choice_model')],
        [InlineKeyboardButton(
            text=f"🖥️ Разрешение: {settings['width']}x{settings['height']}",
            callback_data='resolution')],
        [InlineKeyboardButton(
            text=f"👣 Шагов: {settings['steps']}",
            callback_data='steps')],
        [InlineKeyboardButton(
            text=f"🌡️ Cfg: {settings['guidance_scale']}",
            callback_data='guidance_scale')],
        [InlineKeyboardButton(
            text=f"🧬 Сид: {settings['seed'] if settings['seed'] != '' else 'рандом'}",
            callback_data='seed')],
        [InlineKeyboardButton(text=f"🧩 CUDA: {'True' if settings['cuda'] else 'False'}", callback_data='cuda')],
        [InlineKeyboardButton(text=f"🎛️ Scheduler: {settings['scheduler']}", callback_data='scheduler')],
        [InlineKeyboardButton(text="🖼️ Loras", callback_data='lora')],
        [InlineKeyboardButton(text="️⬅️ Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_model_menu(user_id):
    model = await get_hsettings(user_id, 'model')
    kb = [
        [InlineKeyboardButton(text=model, callback_data=model)] for model in MODELS.keys()
    ]
    kb.append([InlineKeyboardButton(text="️⬅️ Назад", callback_data='model_settings')])
    return InlineKeyboardMarkup(inline_keyboard=kb), model


async def get_scheduler_menu(user_id):
    scheduler = dict(await get_hsettings(user_id))['scheduler']
    kb = [
        [InlineKeyboardButton(text=scheduler, callback_data=scheduler)] for scheduler in SCHEDULERS
    ]
    kb.append([InlineKeyboardButton(text="️⬅️ Назад", callback_data='model_settings')])
    return InlineKeyboardMarkup(inline_keyboard=kb), scheduler


async def get_lora_menu(user_id, loras):
    print(loras)
    current_page = await get_hsettings(user_id, 'page_loras')
    length_loras = len(LORAS_COLUMNS)
    pages = length_loras // LORAS_ROWS + 1
    if current_page is not None:
        loras_columns = LORAS_COLUMNS[LORAS_ROWS * (current_page - 1) : LORAS_ROWS * current_page] if LORAS_ROWS * current_page < length_loras else LORAS_COLUMNS[LORAS_ROWS * (current_page - 1) :]
        # print(loras_columns, pages, current_page)
    else:
        loras_columns = LORAS_COLUMNS
        # print(loras_columns)
    kb = [
        [
            InlineKeyboardButton(text=f'✅ {row[0]}' if row[0] in loras else f'❎ {row[0]}', callback_data=row[0]),
            InlineKeyboardButton(text=f'✅ {row[1]}' if row[1] in loras else f'❎ {row[1]}', callback_data=row[1])
        ] for row in loras_columns[:-1]
    ]
    kb.append([
        InlineKeyboardButton(text=f'✅ {loras_columns[-1][0]}' if loras_columns[-1][0] in loras else f'❎ {loras_columns[-1][0]}', callback_data=loras_columns[-1][0]),
        InlineKeyboardButton(text=f'✅ {loras_columns[-1][1]}' if loras_columns[-1][1] in loras else f'❎ {loras_columns[-1][1]}', callback_data=loras_columns[-1][1])
    ]) if len(loras_columns[-1]) == 2 else kb.append([
        InlineKeyboardButton(text=f'✅ {loras_columns[-1][0]}' if loras_columns[-1][0] in loras else f'❎ {loras_columns[-1][0]}', callback_data=loras_columns[-1][0])
    ])
    if current_page is not None:
        if current_page == 1:
            kb.append([InlineKeyboardButton(text="️⬇️ Выйти", callback_data='model_settings'), InlineKeyboardButton(text="️➡️", callback_data='next_lora')])
        elif current_page == pages:
            kb.append([InlineKeyboardButton(text="️⬅️", callback_data='back_lora'), InlineKeyboardButton(text="️⬇️ Выйти", callback_data='model_settings')])
        elif 1 < current_page < pages:
            kb.append([InlineKeyboardButton(text="️⬅️", callback_data='back_lora'), InlineKeyboardButton(text="️⬇️", callback_data='model_settings'), InlineKeyboardButton(text="️➡️", callback_data='next_lora')])
    else:
        kb.append([InlineKeyboardButton(text="️⬇️ Выйти", callback_data='model_settings')])
    return InlineKeyboardMarkup(inline_keyboard=kb)
