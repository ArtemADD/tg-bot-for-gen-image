from diffusers import DiffusionPipeline
from config import MODEL
import torch
import random


'''
    Загружаем модель (с float16 для ГП)
    У меня AMD карточка с 16 гб поэтому модель нужно разгружать на ЦП
    pipe.enable_attention_slicing() - тоже снижает нагрузку на ГП
    Если была бы карта nvidia, то можно было просто pipe.to("cuda")
'''
def init():
    pipe = DiffusionPipeline.from_pretrained(
        MODEL,
        torch_dtype=torch.float16,
        local_files_only=True
    )
    pipe.enable_attention_slicing()
    pipe.enable_model_cpu_offload()
    # pipe.to("cuda" if torch.cuda.is_available() else 'cpu') # Для nvidia карт
    return pipe


'''
    Генерация изображения: 
    pipe - модель, загружаемая в init()
    settings - настройки пользователя для генерации
'''
def gen_img(pipe, **settings):
    if settings['seed'] == '': # Рандомим сид если не задан
        seed = random.randint(10000000, 100000000)
    else:
        seed = settings['seed']
    image = pipe(
        prompt=settings['prompt'], # Указываем промпт
        negative_prompt=settings['negative_prompt'], # Указываем негативный промпт
        num_inference_steps=settings['steps'],  # Шаги для улучшения качества
        guidance_scale=8.5,     # Чёт делает для точности модели. Поэтому фиксированное значение
        width=settings['width'],              # Ширина изображения
        height=settings['height'],             # Высота изображения
        generator=torch.Generator("cuda").manual_seed(seed)     # Добавляем сид
    ).images[0]
    return image, str(seed) # Возвращаем изображение и сид
    # return 'image', str(seed) # для отладки
