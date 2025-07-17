from types import NoneType
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, BigInteger, Float, Boolean, orm, ForeignKey, Identity, Table, Column


class Base(DeclarativeBase):
    pass


class Models(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default='')
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class Loras(Base):
    __tablename__ = "loras"

    id: Mapped[int] = mapped_column(Integer, Identity(start=1), primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default='')
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)


user_settings_loras = Table(
    "user_settings_loras",
    Base.metadata,
    Column("user_settings_id", BigInteger, ForeignKey("user_settings.id", ondelete="CASCADE"), primary_key=True),
    Column("lora_id", Integer, ForeignKey("loras.id", ondelete="CASCADE"), primary_key=True)
)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    last_img: Mapped[int] = mapped_column(BigInteger, nullable=True)
    prompt: Mapped[str] = mapped_column(String, default="")
    negative_prompt: Mapped[str] = mapped_column(String, default="")
    width: Mapped[int] = mapped_column(Integer, default=1280)
    height: Mapped[int] = mapped_column(Integer, default=1280)
    guidance_scale: Mapped[float] = mapped_column(Float, default=7.0)
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey('models.id', ondelete="SET NULL"), nullable=True)
    scheduler: Mapped[str] = mapped_column(String, default=None, nullable=True)
    cuda: Mapped[bool] = mapped_column(Boolean, default=False)
    num_images: Mapped[int] = mapped_column(Integer, default=1)
    steps: Mapped[int] = mapped_column(Integer, default=30)
    seed: Mapped[int] = mapped_column(Integer, nullable=True)
    model = orm.relationship('Models', lazy="joined", passive_deletes=True)
    loras: Mapped[list[Loras]] = orm.relationship(
        "Loras",
        secondary=user_settings_loras,
        lazy="joined",
        passive_deletes = True
    )
