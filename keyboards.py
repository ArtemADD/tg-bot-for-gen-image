from config import LOADED_MODELS, SCHEDULERS
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
        [InlineKeyboardButton(text="️⬅️ Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_model_menu(user_id):
    model = dict(await get_hsettings(user_id))['model']
    kb = [
        [InlineKeyboardButton(text=model, callback_data=model)] for model in LOADED_MODELS.keys()
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
