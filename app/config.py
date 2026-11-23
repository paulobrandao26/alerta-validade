"""Configuração lida das variáveis de ambiente (ou do arquivo .env)."""

import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AMBIENTES = {"desenvolvimento", "teste", "producao"}


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ambiente: str = "desenvolvimento"
    database_url: str = "sqlite:///./dados/validade.db"
    migrar_ao_iniciar: bool = True

    # Sessão
    secret_key: str = ""
    sessao_horas: int = 12

    # Fotos
    pasta_uploads: str = "./dados/uploads"
    upload_max_bytes: int = 5 * 1024 * 1024

    # IA: provedores na ordem em que são tentados. Se um falhar (limite grátis do dia,
    # fora do ar), o próximo assume. Só entram os que têm chave (ou URL, no caso do Ollama).
    ia_provedores: str = "gemini,groq,ollama"
    gemini_api_key: str = ""
    gemini_modelo: str = "gemini-3.5-flash-lite"
    groq_api_key: str = ""
    groq_modelo: str = "qwen/qwen3.8-27b"
    ollama_url: str = ""  # ex.: http://localhost:11434 (IA rodando no próprio computador)
    ollama_modelo: str = "qwen2.5vl:7b"
    ia_timeout_segundos: float = 30.0
    ia_confianca_minima: float = 0.75
    leitura_max_tentativas: int = 3

    # true = a IA lê a foto durante a própria requisição, sem fila nem worker e sem gravar
    # a foto em disco. É o modo de hospedagens que "dormem" entre acessos (ex.: Vercel).
    leitura_imediata: bool = False

    # Fila
    worker_embutido: bool = True
    worker_intervalo_segundos: float = 2.0

    # Limites contra abuso
    login_max_tentativas: int = 5
    login_janela_segundos: int = 300
    fotos_por_minuto: int = 20

    # Horário da loja (Recife não tem horário de verão)
    fuso_horas: int = -3

    @model_validator(mode="after")
    def _validar(self) -> "Configuracao":
        if self.ambiente not in AMBIENTES:
            raise ValueError(f"AMBIENTE deve ser um de {sorted(AMBIENTES)}")
        # Supabase e outros entregam "postgresql://" ou "postgres://"; o driver instalado é o psycopg 3.
        for prefixo in ("postgresql://", "postgres://"):
            if self.database_url.startswith(prefixo):
                self.database_url = "postgresql+psycopg://" + self.database_url[len(prefixo) :]
        if self.producao:
            if len(self.secret_key) < 32:
                raise ValueError("Em produção, SECRET_KEY é obrigatória e precisa ter 32+ caracteres")
        elif not self.secret_key:
            # Em desenvolvimento, uma chave aleatória por execução: as sessões caem ao reiniciar.
            self.secret_key = secrets.token_urlsafe(48)
        return self

    @property
    def producao(self) -> bool:
        return self.ambiente == "producao"

    @property
    def provedores_ativos(self) -> list[str]:
        disponiveis = {"gemini": self.gemini_api_key, "groq": self.groq_api_key, "ollama": self.ollama_url}
        ordem = [p.strip().lower() for p in self.ia_provedores.split(",") if p.strip()]
        return [p for p in ordem if disponiveis.get(p)]

    @property
    def ia_configurada(self) -> bool:
        return bool(self.provedores_ativos)


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
