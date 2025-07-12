from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, BigInteger, Float, Boolean

class Base(DeclarativeBase):
    async def to_dict(self):
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    last_img: Mapped[int] = mapped_column(BigInteger, nullable=True)
    prompt: Mapped[str] = mapped_column(String, default="")
    negative_prompt: Mapped[str] = mapped_column(String, default="")
    width: Mapped[int] = mapped_column(Integer, default=1280)
    height: Mapped[int] = mapped_column(Integer, default=1280)
    guidance_scale: Mapped[float] = mapped_column(Float, default=7.0)
    model: Mapped[str] = mapped_column(String, default='Anime (Heartsync)')
    scheduler: Mapped[str] = mapped_column(String, default='Euler')
    cuda: Mapped[bool] = mapped_column(Boolean, default=False)
    num_images: Mapped[int] = mapped_column(Integer, default=1)
    steps: Mapped[int] = mapped_column(Integer, default=30)
    seed: Mapped[int] = mapped_column(Integer, nullable=True)
