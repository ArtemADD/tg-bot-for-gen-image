from typing import Optional
from pydantic import BaseModel, field_serializer, field_validator


class BaseSchema(BaseModel):
    class Config:
        from_attributes=True
        arbitrary_types_allowed = True


class ModelSchema(BaseSchema):
    id: int | None = None
    name: str
    description: str
    path: str


class LoraSchema(BaseSchema):
    id: int | None = None
    name: str
    description: str
    path: str


class UserSchema(BaseSchema):
    id: int
    last_img: int | None
    prompt: str
    negative_prompt: str
    width: int
    height: int
    guidance_scale: float
    model_id: int | None
    scheduler: str | None
    cuda: bool | Optional[int]
    num_images: int
    steps: int
    seed: int | None
    loras: Optional[str] | list[int | None]

    @field_serializer('loras')
    def serialize_lora(self, loras: list[dict] | None) -> str:
        if loras != [] and loras != [None] and type(loras) == list:
            return ';'.join([f'{lora}' for lora in loras])
        return ''

    @field_validator('loras', mode='before')
    def validate_loras(cls, loras: str | list) -> list | list[None]:
        if loras != [] and type(loras) != str:
            r = [lora.id for lora in loras]
            return r
        if loras != '' and type(loras) == str:
            r = [int(lora) for lora in loras.split(';')]
            return r
        return []

    @field_serializer('model_id')
    def serialize_model(self, model_id: int | None) -> str | None:
        if model_id:
            return str(model_id)
        return ''

    @field_validator('model_id', mode='before')
    def validate_model(cls, model_id: int | str) -> str | int | None:
        if type(model_id) == int:
            return model_id
        if model_id != '' and type(model_id) == str:
            return int(model_id)
        return None

    @field_serializer('cuda')
    def serialize_cuda(self, cuda: bool) -> str:
        if cuda:
            return '1'
        return '0'

    @field_validator('cuda', mode='before')
    def validate_cuda(cls, cuda: str | bool) -> bool:
        if int(cuda):
            return True
        return False

    @field_serializer('seed')
    def serialize_seed(self, seed: int | None ) -> int | str:
        if seed:
            return seed
        return ''

    @field_validator('seed', mode='before')
    def validate_seed(cls, seed: int | None) -> int | None:
        if seed:
            return seed
        return None

    @field_serializer('scheduler')
    def serialize_scheduler(self, scheduler: str | None ) -> str:
        if scheduler:
            return scheduler
        return ''

    @field_validator('scheduler', mode='before')
    def validate_scheduler(cls, scheduler: str | None) -> str | None:
        if scheduler:
            return scheduler
        return None
