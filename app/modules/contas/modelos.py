from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.nucleo.relogio import agora_utc


class Loja(Base):
    __tablename__ = "lojas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    dias_alerta: Mapped[int] = mapped_column(Integer, default=7)
    whatsapp: Mapped[str | None] = mapped_column(String(13), default=None)
    criado_em: Mapped[datetime] = mapped_column(default=agora_utc)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    loja_id: Mapped[int] = mapped_column(ForeignKey("lojas.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(default=agora_utc)

    loja: Mapped[Loja] = relationship(lazy="joined")
