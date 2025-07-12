from os import PathLike
from PIL.Image import Image
from diffusers import DiffusionPipeline, LCMScheduler, StableDiffusionXLPipeline, DPMSolverMultistepScheduler, EulerAncestralDiscreteScheduler
import torch
import random


LORA_LCM = 'latent-consistency/lcm-lora-sdxl'


class ModelLoader:
    def __init__(self, model=None, scheduler=None, lora=None, cuda=False):
        """
            Загружаем модель (с float16 для ГП)
            У меня AMD карточка с 16 гб поэтому модель нужно разгружать на ЦП
            pipe.enable_attention_slicing() - тоже снижает нагрузку на ГП
            Если была бы карта nvidia, то можно было просто pipe.to("cuda")
        """
        self.model: [str | None | PathLike]
        self.scheduler: [str | None]
        self.lora: [str | None]
        self.pipe: [None | DiffusionPipeline]
        self.cuda: bool
        self.model = model
        self.scheduler = scheduler
        self.lora = lora
        self.pipe = None
        self.cuda = cuda

    def set_model(self, model: str):
        self.model = model

    def set_scheduler(self, scheduler: [str | None]):
        self.scheduler = scheduler

    def set_lora(self, lora: str | None):
        self.lora = lora

    def set_cuda(self, cuda: bool):
        self.cuda = cuda

    def init_model(self):
        try:
            print(f'Load {self.model} to pipeline')
            if self.model:
                if '.safetensors' in self.model:
                    self.pipe = StableDiffusionXLPipeline.from_single_file(
                        self.model,
                        torch_dtype=torch.float16
                    )
                else:
                    self.pipe = DiffusionPipeline.from_pretrained(
                        self.model,
                        torch_dtype=torch.float16
                    )
                if self.scheduler:
                    print(self.pipe.scheduler.config)
                    match self.scheduler:
                        case 'LCM':
                            self.pipe.scheduler = LCMScheduler.from_config(self.pipe.scheduler.config, use_karras_sigmas=True)
                        case 'DPM':
                            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(self.pipe.scheduler.config, solver_order=3, use_karras_sigmas=True)
                        case 'Euler':
                            self.pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(self.pipe.scheduler.config, use_karras_sigmas=True)
                            self.pipe.load_lora_weights(LORA_LCM, adapter_name="lora_lcm")
                            self.pipe.set_adapters("lora_lcm", adapter_weights=0.8)
                    print(f'Scheduler {self.scheduler}: done')
                else:
                    print('No scheduler')
                self.pipe.enable_attention_slicing()
                self.pipe.enable_model_cpu_offload()
                self.pipe.enable_xformers_memory_efficient_attention()
                if self.cuda:
                    self.pipe.to("cuda") # Для nvidia карт
                    print('Cuda done')
                else:
                    print('No cuda')
                if self.lora:
                    self.pipe.load_lora_weights(self.lora, adapter_name="lora")
                    self.pipe.set_adapters("lora", adapter_weights=0.8)
                    print('Lora done')
                else:
                    print('No lora')
                print('Pipeline done')
                return self.pipe
            return None
        except Exception as e:
            raise e

    def gen_img(self, **settings) -> (Image, str):
        """
            Генерация изображения:
            pipe - модель, загружаемая в init()
            settings - настройки пользователя для генерации
        """
        if self.pipe:
            if settings['seed'] in ['', None] : # Рандомим сид если не задан
                seed = random.randint(10000000, 100000000)
            else:
                seed = settings['seed']
            image = self.pipe(
                prompt=settings['prompt'], # Указываем промпт
                negative_prompt=settings['negative_prompt'], # Указываем негативный промпт
                num_inference_steps=settings['steps'],  # Шаги для улучшения качества
                guidance_scale=settings['guidance_scale'],  # Чёт делает для точности модели. Поэтому фиксированное значение
                width=settings['width'],              # Ширина изображения
                height=settings['height'],             # Высота изображения
                generator=torch.Generator("cuda").manual_seed(seed)     # Добавляем сид
            ).images[0]
            return image, str(seed) # Возвращаем изображение и сид
            # return 'image', str(seed) # для отладки
        return Exception

    def copy(self):
        return ModelLoader(self.model, self.scheduler, self.lora, self.cuda)

    def __call__(self):
        if self.pipe:
            return self.pipe
        return self.init_model()

    def __str__(self):
        return f'Model: {self.model}\nScheduler: {self.scheduler}\nLora: {self.lora}\nCuda: {self.cuda}\nPipe: {self.pipe}'
