from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.nucleo.relogio import agora_utc


class StatusLeitura(StrEnum):
    PENDENTE = "pendente"  # na fila, esperando o worker
    PROCESSANDO = "processando"  # o worker pegou e está chamando a IA
    LIDA = "lida"  # a IA leu com boa confiança; falta a pessoa confirmar
    REVISAO = "revisao"  # a IA não conseguiu (ou teve pouca confiança): a pessoa preenche
    CONFIRMADA = "confirmada"  # virou um lote


class Leitura(Base):
    """Uma foto de embalagem enviada para a IA ler. Também é o item da fila."""

    __tablename__ = "leituras"

    id: Mapped[int] = mapped_column(primary_key=True)
    loja_id: Mapped[int] = mapped_column(ForeignKey("lojas.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    arquivo: Mapped[str] = mapped_column(String(64))
    mime: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(12), default=StatusLeitura.PENDENTE, index=True)
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    proxima_tentativa_em: Mapped[datetime] = mapped_column(default=agora_utc)
    produto_lido: Mapped[str | None] = mapped_column(String(120), default=None)
    validade_lida: Mapped[date | None] = mapped_column(default=None)
    confianca: Mapped[float | None] = mapped_column(Float, default=None)
    erro: Mapped[str | None] = mapped_column(String(200), default=None)
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id", ondelete="SET NULL"), default=None)
    criado_em: Mapped[datetime] = mapped_column(default=agora_utc)
    atualizado_em: Mapped[datetime] = mapped_column(default=agora_utc, onupdate=agora_utc)
