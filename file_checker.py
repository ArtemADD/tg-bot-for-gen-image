from red import *
import db
from db_models import UserSettings, Models, Loras
from pd_schema import UserSchema, LoraSchema, ModelSchema
import os


LOCAL = 'local/'
LOCAL_MODELS = 'local/models/'
LOCAL_LORAS = 'local/loras/'


async def check_loras(user_loras, loras: UserSchema):
    # loras_from_redis = await
    return loras


async def check_models_files():
    loaded = []
    deleted = []
    models_in_db = await db.get_all(Models)
    os.chdir(f'{os.getcwd()}/{LOCAL_MODELS}')
    models_in_local_dir = [path for path in os.listdir() if '.safetensors' in path and ('ILXL' in path or 'Illustrious' in path)]
    for local_model in models_in_local_dir:
        if any(map(lambda x: LOCAL_MODELS + local_model == x.path, models_in_db)):
            continue
        name = local_model.rstrip('.safetensors')
        await db.add_model(path=LOCAL_MODELS + local_model, name=name)
        loaded.append(name)
    for db_models in models_in_db:
        if any(map(lambda x: (db_models.path ==  LOCAL_MODELS + x or '.safetensors' not in db_models.path), models_in_local_dir)):
            continue
        await db.del_model(db_models.id)
        deleted.append(db_models.name)
    os.chdir('../..')
    if loaded:
        print('Loaded Local Models:', *loaded)
    if deleted:
        print('Deleted DB Models:', *deleted)


async def check_loras_files():
    loaded = []
    deleted = []
    loras_in_db = await db.get_all(Loras)
    os.chdir(f'{os.getcwd()}/{LOCAL_LORAS}')
    loras_in_local_dir = [path for path in os.listdir() if '.safetensors' in path]
    for local_loras in loras_in_local_dir:
        if any(map(lambda x: local_loras == x.path, loras_in_db)):
            continue
        name = local_loras.rstrip('.safetensors')
        await db.add_lora(path=local_loras, name=name)
        loaded.append(name)
    for db_loras in loras_in_db:
        if  any(map(lambda x: (db_loras.path == x or '.safetensors' not in db_loras), loras_in_local_dir)):
            continue
        await db.del_lora(db_loras.id)
        deleted.append(db_loras.name)
    os.chdir('../..')
    if loaded:
        print('Loaded Local Loras:', *loaded)
    if deleted:
        print('Deleted DB Loras:', *deleted)


async def start_check():
    await check_models_files()
    await check_loras_files()
    await load_to_h_ml()
    await check_h_models()
    await check_h_loras()
