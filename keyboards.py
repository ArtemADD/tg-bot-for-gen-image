from config import SCHEDULERS, LORAS_ROWS # , LORAS_COLUMNS
import db
from db_models import Models, UserSettings, Loras
from pd_schema import UserSchema, ModelSchema, LoraSchema
import red
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def shorten(text, max_len=25):
    return text[:max_len] + "..." if text and len(text) > max_len else (text or "не задано")


async def get_base_settings_menu(user_id):
    user = await red.get_h_user(user_id)
    kb = [
        # [InlineKeyboardButton(text="🎨 Сгенерировать", callback_data='generate')],
        [InlineKeyboardButton(
            text=f"✨ Промпт: {shorten(user.prompt) if user.prompt else 'Не задан'}",
            callback_data='prompt')],
        [InlineKeyboardButton(
            text=f"💥 Негативный промпт: {shorten(user.negative_prompt) if user.prompt else 'Не задан'}",
            callback_data='negative_prompt')],
        [InlineKeyboardButton(
            text=f"🔢 Кол-во изображений: {user.num_images if user.seed == '' else 'Установлен сид'}",
            callback_data='num_images')],
        [InlineKeyboardButton(
            text="️⚙️ Настройки Модели",
            callback_data='model_settings')],
        [InlineKeyboardButton(text="🎨 Сгенерировать", callback_data='generate')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_model_settings_menu(user_id):
    user  = await red.get_h_user(user_id)
    if not (model := await red.get_h_model(user.model_id)):
        model = None
    kb = [
        [InlineKeyboardButton(text=f"🧠 Модель: {model.name}⠀" if model else f"🧠 Модель не выбрана.", callback_data='choice_model')],
        [InlineKeyboardButton(
            text=f"🖥️ Разрешение: {user.width}x{user.height}",
            callback_data='resolution')],
        [InlineKeyboardButton(
            text=f"👣 Шагов: {user.steps}",
            callback_data='steps')],
        [InlineKeyboardButton(
            text=f"🌡️ Cfg: {user.guidance_scale}",
            callback_data='guidance_scale')],
        [InlineKeyboardButton(
            text=f"🧬 Сид: {user.seed if user.seed != '' else 'рандом'}",
            callback_data='seed')],
        [InlineKeyboardButton(text=f"🧩 CUDA: {'True' if user.cuda else 'False'}", callback_data='cuda')],
        [InlineKeyboardButton(text=f"🎛️ Scheduler: {user.scheduler}", callback_data='scheduler')],
        [InlineKeyboardButton(text="🖼️ Loras", callback_data='lora')],
        [InlineKeyboardButton(text="️↩️ Назад", callback_data='back'), InlineKeyboardButton(text="🎨", callback_data='generate')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_model_menu():
    models = await red.get_h_models()
    kb = [
        [InlineKeyboardButton(text=str(model.name), callback_data=f'model:{str(model.id)}')] for model in models
    ]
    kb.append([InlineKeyboardButton(text="️↩️ Назад", callback_data='model_settings'), InlineKeyboardButton(text="🎨", callback_data='generate')])
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_scheduler_menu(user_id):
    scheduler = await red.get_h_user(user_id, 'scheduler')
    kb = [
        [InlineKeyboardButton(text=scheduler, callback_data=scheduler)] for scheduler in SCHEDULERS
    ]
    kb.append([InlineKeyboardButton(text="️↩️ Назад", callback_data='model_settings'), InlineKeyboardButton(text="🎨", callback_data='generate')])
    return InlineKeyboardMarkup(inline_keyboard=kb), scheduler


async def get_lora_menu(user_id, h_loras):
    # print(loras)
    current_page = await red.get_h_user(user_id, 'page_loras')
    user_loras = await red.get_h_user(user_id, 'loras')
    length_loras = len(h_loras)
    pages = length_loras // LORAS_ROWS + 1
    if current_page is not None:
        loras_columns = h_loras[LORAS_ROWS * (current_page - 1) : LORAS_ROWS * current_page] if LORAS_ROWS * current_page < length_loras else h_loras[LORAS_ROWS * (current_page - 1) :]
        # print(loras_columns, pages, current_page)
    else:
        loras_columns = h_loras
        # print(loras_columns)
    # print(loras_columns)
    kb = [
        [
            InlineKeyboardButton(text=f'✅ {row.name}󠀠󠀠󠀠󠀠󠁜' if row.id in user_loras else f'❌ {row.name}', callback_data=f'lora:{row.id}'), InlineKeyboardButton(text='Подробнее ℹ️', callback_data=f'description:lora:{row.id}')
        ] for row in loras_columns
    ]
    if current_page is not None:
        if current_page == 1:
            kb.append([
                InlineKeyboardButton(text="󠀠󠀠󠀠󠀠󠁜⠀", callback_data='zxc'),
                InlineKeyboardButton(text="️↩️", callback_data='model_settings'),
                InlineKeyboardButton(text="🎨", callback_data='generate'),
                InlineKeyboardButton(text="️➡️", callback_data='next_lora')
            ])
        elif current_page == pages:
            kb.append([
                InlineKeyboardButton(text="️⬅️", callback_data='back_lora'),
                InlineKeyboardButton(text="️↩️", callback_data='model_settings'),
                InlineKeyboardButton(text="🎨", callback_data='generate'),
                InlineKeyboardButton(text="️⠀", callback_data='zxc')
            ])
        elif 1 < current_page < pages:
            kb.append([
                InlineKeyboardButton(text="️⬅️", callback_data='back_lora'), InlineKeyboardButton(text="️↩️", callback_data='model_settings'),
                InlineKeyboardButton(text="🎨", callback_data='generate'), InlineKeyboardButton(text="️➡️", callback_data='next_lora')
            ])
    else:
        kb.append([InlineKeyboardButton(text="️↩️", callback_data='model_settings'), InlineKeyboardButton(text="🎨", callback_data='generate')])
    return InlineKeyboardMarkup(inline_keyboard=kb)
