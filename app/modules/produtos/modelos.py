from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.nucleo.relogio import agora_utc


class Situacao(StrEnum):
    ATIVO = "ativo"
    VENDIDO = "vendido"
    DESCARTADO = "descartado"


class Origem(StrEnum):
    MANUAL = "manual"
    FOTO = "foto"
    PRAZO = "prazo"


class Produto(Base):
    __tablename__ = "produtos"
    __table_args__ = (UniqueConstraint("loja_id", "nome_chave", name="uq_produtos_loja_nome"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    loja_id: Mapped[int] = mapped_column(ForeignKey("lojas.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    # Nome em minúsculas e sem espaços extras: evita "Leite" e "leite " duplicados.
    nome_chave: Mapped[str] = mapped_column(String(120))
    codigo_barras: Mapped[str | None] = mapped_column(String(14), default=None)
    # Para frescos sem data impressa (pão, frios): validade = chegada + N dias.
    prazo_padrao_dias: Mapped[int | None] = mapped_column(Integer, default=None)
    criado_em: Mapped[datetime] = mapped_column(default=agora_utc)


class Lote(Base):
    __tablename__ = "lotes"
    __table_args__ = (CheckConstraint("quantidade > 0", name="quantidade_positiva"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    loja_id: Mapped[int] = mapped_column(ForeignKey("lojas.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id", ondelete="CASCADE"), index=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    validade: Mapped[date] = mapped_column(index=True)
    situacao: Mapped[str] = mapped_column(String(12), default=Situacao.ATIVO)
    origem: Mapped[str] = mapped_column(String(10), default=Origem.MANUAL)
    criado_em: Mapped[datetime] = mapped_column(default=agora_utc)
    baixado_em: Mapped[datetime | None] = mapped_column(default=None)

    produto: Mapped[Produto] = relationship(lazy="joined")
