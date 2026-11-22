import json
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.modules.produtos.schemas import normalizar_nome


class RespostaIAInvalida(Exception):
    """A IA respondeu algo fora do formato combinado."""


class RespostaIA(BaseModel):
    """O formato exato que a IA precisa devolver. Qualquer coisa diferente é rejeitada."""

    model_config = ConfigDict(extra="ignore")

    produto: str | None = Field(default=None, max_length=120)
    validade: date | None = None
    confianca: float = Field(ge=0, le=1)

    @field_validator("produto")
    @classmethod
    def _produto(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = normalizar_nome(valor)
        return valor if len(valor) >= 2 else None


_BLOCO_JSON = re.compile(r"\{.*\}", re.DOTALL)


def interpretar_resposta(texto: str) -> RespostaIA:
    """Extrai e valida o JSON da resposta da IA."""
    achado = _BLOCO_JSON.search(texto or "")
    if not achado:
        raise RespostaIAInvalida("A resposta não tem JSON.")
    try:
        return RespostaIA.model_validate(json.loads(achado.group(0)))
    except (json.JSONDecodeError, ValidationError) as erro:
        raise RespostaIAInvalida("O JSON da resposta não segue o formato.") from erro


def data_plausivel(validade: date, hoje: date) -> bool:
    """Uma validade de mais de 1 ano atrás ou mais de 5 anos à frente é quase sempre erro de leitura."""
    return -365 <= (validade - hoje).days <= 365 * 5


class Confirmacao(BaseModel):
    produto_nome: str = Field(min_length=2, max_length=120)
    validade: date
    quantidade: int = Field(ge=1, le=100_000)

    _nome = field_validator("produto_nome")(normalizar_nome)


class LeituraSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    produto_lido: str | None
    validade_lida: date | None
    confianca: float | None
    erro: str | None
    lote_id: int | None
