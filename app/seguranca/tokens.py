"""Token de sessão (JWT assinado), guardado num cookie httpOnly."""

from datetime import UTC, datetime, timedelta

import jwt

ALGORITMO = "HS256"
NOME_COOKIE = "vc_sessao"


def criar_token(usuario_id: int, chave: str, horas: int) -> str:
    agora = datetime.now(UTC)
    dados = {"sub": str(usuario_id), "iat": agora, "exp": agora + timedelta(hours=horas)}
    return jwt.encode(dados, chave, algorithm=ALGORITMO)


def ler_token(token: str, chave: str) -> int | None:
    """Devolve o id do usuário, ou None se o token for inválido ou estiver vencido."""
    try:
        dados = jwt.decode(token, chave, algorithms=[ALGORITMO], options={"require": ["exp", "sub"]})
        return int(dados["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
