import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _limpar_email(valor: str) -> str:
    return valor.strip().lower()


class Cadastro(BaseModel):
    nome_loja: str = Field(min_length=2, max_length=80)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)

    _email = field_validator("email", mode="before")(_limpar_email)

    @field_validator("nome_loja")
    @classmethod
    def _nome(cls, valor: str) -> str:
        valor = " ".join(valor.split())
        if len(valor) < 2:
            raise ValueError("Informe o nome da loja.")
        return valor


class Entrada(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)

    _email = field_validator("email", mode="before")(_limpar_email)


class AjustesLoja(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=80)
    dias_alerta: int | None = Field(default=None, ge=1, le=60)
    whatsapp: str | None = Field(default=None, max_length=20)

    @field_validator("whatsapp")
    @classmethod
    def _whatsapp(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        digitos = re.sub(r"\D", "", valor)
        if digitos == "":
            return ""
        if digitos.startswith("55") and len(digitos) in (12, 13):
            digitos = digitos[2:]
        if len(digitos) not in (10, 11):
            raise ValueError("Use DDD + número, ex.: 81 99999-9999.")
        return digitos


class LojaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    dias_alerta: int
    whatsapp: str | None


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class Conta(BaseModel):
    usuario: UsuarioSaida
    loja: LojaSaida
    ia_ligada: bool
