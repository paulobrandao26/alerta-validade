from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalizar_nome(valor: str) -> str:
    return " ".join(valor.split())


class NovoLote(BaseModel):
    produto_nome: str = Field(min_length=2, max_length=120)
    quantidade: int = Field(ge=1, le=100_000)
    validade: date | None = None
    codigo_barras: str | None = Field(default=None, pattern=r"^\d{8,14}$")
    # Só usado quando o produto é novo e não tem data impressa.
    prazo_padrao_dias: int | None = Field(default=None, ge=1, le=60)

    _nome = field_validator("produto_nome")(normalizar_nome)


class Baixa(BaseModel):
    motivo: Literal["vendido", "descartado"]


class ProdutoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    codigo_barras: str | None
    prazo_padrao_dias: int | None


class LoteSaida(BaseModel):
    id: int
    produto_id: int
    produto_nome: str
    quantidade: int
    validade: date
    dias_restantes: int
    estado: Literal["vencido", "atencao", "ok"]
    situacao: str
    origem: str
