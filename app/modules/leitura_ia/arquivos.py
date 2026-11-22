"""Validação e gravação das fotos enviadas.

O tipo do arquivo é descoberto pelos primeiros bytes (a "assinatura"), e não pelo
nome ou pelo Content-Type, que o navegador (ou um atacante) pode mentir.
"""

import re
import secrets
from pathlib import Path

from app.nucleo.erros import DadosInvalidos

ASSINATURAS = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
EXTENSOES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
# Só aceitamos nomes que nós mesmos geramos: 32 caracteres hexadecimais + extensão.
NOME_VALIDO = re.compile(r"[0-9a-f]{32}\.(jpg|png|webp)")


def descobrir_tipo(conteudo: bytes) -> str | None:
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp"
    for mime, prefixos in ASSINATURAS.items():
        if any(conteudo.startswith(p) for p in prefixos):
            return mime
    return None


def validar_foto(conteudo: bytes, limite_bytes: int) -> str:
    if not conteudo:
        raise DadosInvalidos("A foto está vazia.")
    if len(conteudo) > limite_bytes:
        raise DadosInvalidos(f"A foto passou de {limite_bytes // (1024 * 1024)} MB.")
    mime = descobrir_tipo(conteudo)
    if mime is None:
        raise DadosInvalidos("Envie uma foto em JPG, PNG ou WebP.")
    return mime


def salvar_foto(pasta: str | Path, conteudo: bytes, mime: str) -> str:
    """Grava com um nome aleatório (o nome original do arquivo é descartado)."""
    destino = Path(pasta)
    destino.mkdir(parents=True, exist_ok=True)
    nome = secrets.token_hex(16) + EXTENSOES[mime]
    (destino / nome).write_bytes(conteudo)
    return nome


def caminho_seguro(pasta: str | Path, nome: str) -> Path:
    """Monta o caminho garantindo que ele não sai da pasta de fotos."""
    if not NOME_VALIDO.fullmatch(nome or ""):
        raise DadosInvalidos("Arquivo inválido.")
    base = Path(pasta).resolve()
    caminho = (base / nome).resolve()
    if caminho.parent != base:
        raise DadosInvalidos("Arquivo inválido.")
    return caminho
