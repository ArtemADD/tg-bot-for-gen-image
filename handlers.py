from aiogram import Dispatcher
import asyncio
import multiprocessing
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from io import BytesIO
from aiogram import types, F
import db
from ai import ModelLoader
from config import  SCHEDULERS, LORAS_ROWS #, MODELS, LORAS, LORAS_COLUMNS,
import red
from keyboards import get_base_settings_menu, get_model_settings_menu, get_model_menu, get_scheduler_menu, get_lora_menu
from pd_schema import UserSchema, ModelSchema, LoraSchema

# Диспатчер
dp = Dispatcher()

processes = {}
statuses = {}
queues = {}

class BaseSettingsStates(StatesGroup):
    waiting_for_prompt = State()
    edit_lora = State()


async def check_user(msg: Message) -> int:
    user_id = msg.chat.id
    if not await red.check(f'user:{user_id}:settings'):
        user = await db.get_user(user_id)
        await red.add_h_user(user)
    return user_id


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
    await red.check_user_model(callback.message.chat.id)
    if await red.get_h_user(callback.message.chat.id, 'page_loras') is not None: await red.del_h_user_setting(callback.message.chat.id, 'page_loras')
    await show_model_settings(callback.message)


async def show_model_settings(msg: Message, s=False):
    await check_user(msg)
    keyboard = await get_model_settings_menu(msg.chat.id)
    text_msg = '⚙️ Настройки модели'
    await msg.answer(text_msg, reply_markup=keyboard) if s else await msg.edit_text(text_msg, reply_markup=keyboard)


@dp.callback_query(F.data == 'choice_model')
async def choice_model(callback: CallbackQuery):
    await check_user(callback.message)
    await show_model_menu(callback.message)


async def show_model_menu(msg: Message):
    keyboard = await get_model_menu()
    model = await red.get_h_model(await red.get_h_user(msg.chat.id, 'model_id'))
    await msg.edit_text(f'🧠 Текущая модель: {model.name}' if model else f'🧠 Модель не выбрана.', reply_markup=keyboard)


@dp.callback_query(lambda x: x.data.startswith('model:'))
async def set_model(callback: CallbackQuery):
    await check_user(callback.message)
    await red.update_h_user(callback.message.chat.id, 'model_id', int(callback.data.lstrip('model:')))
    await show_model_settings(callback.message)


@dp.callback_query(F.data == 'scheduler')
async def show_scheduler(callback: CallbackQuery):
    await check_user(callback.message)
    keyboard, scheduler = await get_scheduler_menu(callback.message.chat.id)
    await callback.message.edit_text(f'🎛️ Выбор scheduler ({scheduler}):', reply_markup=keyboard)


@dp.callback_query(F.data.in_(SCHEDULERS))
async def set_scheduler(callback: CallbackQuery):
    await check_user(callback.message)
    await red.update_h_user(callback.message.chat.id, 'scheduler', callback.data)
    await show_model_settings(callback.message)


@dp.callback_query(F.data == 'lora')
async def show_loras(callback: CallbackQuery):
    await check_user(callback.message)
    await show_loras_menu(callback.message)


async def show_loras_menu(msg: Message):
    await red.check_h_loras()
    await red.check_user_loras(msg.chat.id)
    p = await red.get_h_user(msg.chat.id, 'page_loras')
    h_loras = await red.get_h_loras()
    if len(h_loras) > LORAS_ROWS and p is None:
        await red.add_h_user_setting(msg.chat.id, 'page_loras', 1)
        keyboard = await get_lora_menu(msg.chat.id, h_loras)
    else:
        keyboard = await get_lora_menu(msg.chat.id, h_loras)
    await msg.edit_text('🖼️ Выбор lora:', reply_markup=keyboard)


@dp.callback_query(lambda x: x.data.startswith('lora:'))
async def set_loras(callback: CallbackQuery):
    await check_user(callback.message)
    print(callback.data)
    await red.update_h_user(callback.message.chat.id, 'loras', int(callback.data.lstrip('lora:')))
    await show_loras_menu(callback.message)


@dp.callback_query(F.data == 'back_lora')
async def back_lora(callback: CallbackQuery):
    await check_user(callback.message)
    p = await red.get_h_user(callback.message.chat.id, 'page_loras')
    if p:
        await red.update_h_user(callback.message.chat.id, 'page_loras', p - 1, h_only=True)
        await show_loras_menu(callback.message)
    else:
        await show_model_settings(callback.message)


@dp.callback_query(F.data == 'next_lora')
async def next_lora(callback: CallbackQuery):
    await check_user(callback.message)
    p = await red.get_h_user(callback.message.chat.id, 'page_loras')
    if p:
        await red.update_h_user(callback.message.chat.id, 'page_loras', p + 1, h_only=True)
        await show_loras_menu(callback.message)
    else:
        await show_model_settings(callback.message)

@dp.callback_query(lambda x: x.data.startswith('description:lora:'))
async def description_lora(callback: CallbackQuery, state: FSMContext):
    await check_user(callback.message)
    await state.clear()
    await show_description_lora(callback.message, state, lora_id=int(callback.data.lstrip('description:lora:')))


async def show_description_lora(msg: Message, state: FSMContext, lora_id):
    if not await red.get_h_user(msg.chat.id, 'page_loras'):
        await show_model_settings(msg)
        await state.clear()
        return
    lora = await red.get_h_lora(lora_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='️📝', callback_data=f'edit:description:lora:{lora.id}')],
        [InlineKeyboardButton(text='️↩️ Назад', callback_data='back_to_lora')]
    ])
    callback = await state.get_data()
    if callback:
        msgs = callback.get('msgs')
        if callback.get('stat'):
            msg_1 = await msgs.edit_text(lora.name, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='️📝', callback_data=f'edit:name:lora:{lora.id}')]
            ]))
            msg_2 = await msg.answer(lora.description if lora.description else 'Нет описания', reply_markup=keyboard)
            await msg.delete()
        else:
            msg_1 = await msgs.edit_text(lora.name, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='️📝', callback_data=f'edit:name:lora:{lora.id}')]
            ]))
            msg_2 = await msg.answer(lora.description if lora.description else 'Нет описания', reply_markup=keyboard)
    else:
        msg_1 = await msg.edit_text(lora.name, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='️📝', callback_data=f'edit:name:lora:{lora.id}')]
        ]))
        msg_2 = await msg.answer(lora.description if lora.description else 'Нет описания', reply_markup=keyboard)
    await state.update_data(msgs=[msg_1, msg_2])
    await state.set_state(BaseSettingsStates.edit_lora)


@dp.callback_query(lambda x: x.data.startswith('edit:description:lora:') or x.data.startswith('edit:name:lora:'))
async def edit_description_lora(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith('edit:description:lora:'):
        lora_id = int(callback.data.lstrip('edit:description:lora:'))
        lora = await red.get_h_lora(lora_id)
        msgs = await state.get_data()
        if not msgs:
            await show_model_settings(callback.message)
            await state.clear()
            return
        msg_1, msg_2 = msgs.get('msgs')
        await msg_1.delete()
        await msg_2.edit_text(lora.description if lora.description else 'Нет описания', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🚫 Оставить без изменений', callback_data=f'description:lora:{lora.id}')]
        ]))
        await state.update_data(msgs=msg_2, set_data='description', lora_id=lora_id)
    elif callback.data.startswith('edit:name:lora:'):
        lora_id = int(callback.data.lstrip('edit:name:lora:'))
        lora = await red.get_h_lora(lora_id)
        msgs = await state.get_data()
        if not msgs:
            await show_model_settings(callback.message)
            await state.clear()
            return
        msg_1, msg_2 = msgs.get('msgs')
        await msg_2.delete()
        msg = await msg_1.edit_text(lora.name, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🚫 Оставить без изменений', callback_data=f'description:lora:{lora.id}')]
        ]))
        await state.update_data(msgs=msg, set_data='name', lora_id=lora_id)


@dp.message(BaseSettingsStates.edit_lora)
async def set_edit_description_lora(msg: Message, state: FSMContext):
    callback = await state.get_data()
    if callback:
        data = callback.get('set_data')
        lora_id = callback.get('lora_id')
        msgs = callback.get('msgs')
        if data == 'description':
            # print(msg.text)
            await red.update_h_lora(lora_id, data, msg.text)
        elif data == 'name':
            # print(msg.text)
            await red.update_h_lora(lora_id, data, msg.text)
    await state.update_data(msgs=msgs, stat='done_edit')
    await show_description_lora(msg, state, lora_id)



@dp.callback_query(F.data == 'back_to_lora')
async def back_description_lora(callback: CallbackQuery, state: FSMContext):
    msgs = await state.get_data()
    if msgs:
        msgs = msgs.get('msgs')
        await msgs[0].delete()
        await state.clear()
        await show_loras_menu(callback.message)
    else:
        await show_model_settings(callback.message)


# @dp.callback_query(lambda x: x.data.startswith('edit:description:lora:'))
# async def show_edit_description_lora(callback: CallbackQuery, state: FSMContext):
#     msgs = await state.get_data()
#     if not msgs:
#         await show_model_settings(callback.message)
#     msgs = msgs.get('msgs')
#     lora = await red.get_h_lora(int(callback.data.lstrip('edit:description:lora:')))
#     msg = await msgs.edit_text(lora.name, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
#         InlineKeyboardButton(text='📝', callback_data=f'edit:name:description:lora:{lora.id}')
#     ]]))
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text='️🔙', callback_data=f'description:lora:{lora.id}'),
#          InlineKeyboardButton(text='📝', callback_data=f'edit:desc:description:lora:{lora.id}')]
#     ])
#     await callback.message.edit_text(lora.description if lora.description else 'Нет описания', reply_markup=keyboard)
#     await state.update_data(setting=callback.data, msgs=msg)
#     await state.set_state(BaseSettingsStates.waiting_for_prompt)


@dp.callback_query(F.data == 'cuda')
async def set_cuda(callback: CallbackQuery):
    await check_user(callback.message)
    cuda = False if await red.get_h_user(callback.message.chat.id, 'cuda') else True
    await red.update_h_user(callback.message.chat.id, 'cuda', cuda)
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
    user = await red.get_h_user(user_id)
    rule_settings = {
        'prompt': user.prompt if user.prompt else 'Введите новый промпт:',
        'negative_prompt': user.negative_prompt if user.negative_prompt else 'Введите негативный промпт:',
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
            await red.update_h_user(user_id, 'width', width)
            await red.update_h_user(user_id,'height', height)
        elif setting == 'num_images':
            await red.update_h_user(user_id,'num_images', int(text))
        elif setting == 'steps':
            await red.update_h_user(user_id,'steps', int(text))
        elif setting == 'seed':
            await red.update_h_user(user_id,'seed', int(text) if text.isdigit() else None)
        elif setting == 'guidance_scale':
            await red.update_h_user(user_id,'guidance_scale', float(text))
        else:
            await red.update_h_user(user_id,setting, text)
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
        print(e.__repr__())
        await message.delete()
        await msg.edit_text(f"Ошибка ввода. Попробуйте снова.\n{e.__repr__()}", reply_markup=keyboard)


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
    user = await red.get_h_user(user_id)
    await red.check_user_loras(user_id)
    await red.check_user_model(user_id)
    model = await red.get_h_model(user.model_id)
    loras = [(await red.get_h_lora(lora)).path for lora in user.loras]
    if not user.model_id:
        await callback.message.edit_text('Выберите модель')
        await asyncio.sleep(3)
        await show_base_settings(callback.message)
    elif user.prompt == '' or user.negative_prompt == '':
        await callback.message.edit_text('Введите промпт или негативный промпт')
        await asyncio.sleep(3)
        await show_base_settings(callback.message)
    elif not list(processes.keys()):
        msg = callback.message
        chat_id = callback.message.chat.id
        q = multiprocessing.Queue(1)
        pr = multiprocessing.Process(target=generate_image, args=(user, model, loras, q,), daemon=True)
        pr.start()
        processes[chat_id] = pr
        statuses[chat_id] = 'pending'
        queues[chat_id] = q
        asyncio.create_task(monitor_generation(chat_id, user_id, msg))
    else:
        await callback.message.edit_text('Извини, уже занят')
        await asyncio.sleep(5)
        await show_base_settings(callback.message)


def generate_image(user: UserSchema, model: ModelSchema, loras: list[LoraSchema], queue):
    try:
        # print(model)
        # print(loras)
        loader = ModelLoader(model=model.path, cuda=user.cuda, scheduler=user.scheduler, lora=loras)
        loader()
        # print(f'{settings}\n{loader}')
        n = user.num_images if not user.seed else 1
        print(f'Generate prompt: {user.prompt}' if user.seed is None else f'Generate prompt: {user.prompt}\nSeed: {user.seed}')
        for _ in range(n):
            response = {}
            image, seed = loader.gen_img(**user.model_dump())
            bio = BytesIO()
            image.save(bio, format='PNG')
            bio.seek(0)
            doc = types.BufferedInputFile(bio.getvalue(), filename=f'img_{model.name}_{seed}.png')
            response['img'] = doc
            queue.put(response)
    except Exception as e:
        # raise e
        print(e.__repr__())
        queue.put({'error': e})


async def monitor_generation(chat_id, user_id, msg):
    s = await red.get_h_user(user_id)
    n = s.num_images if not s.seed else 1
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
            await red.update_h_user(user_id, 'last_img', h.message_id)
    except Exception as e:
        print(e.__repr__())
        await msg.edit_text(f'{e}')
        await asyncio.sleep(6)
    processes[chat_id].terminate()
    processes.pop(chat_id, None)
    queues.pop(chat_id, None)
    statuses.pop(chat_id, None)
    await msg.delete()
    await show_base_settings(msg, s=True)
