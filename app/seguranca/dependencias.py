"""Quem está logado. Toda rota protegida usa `usuario_atual`."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.sessao import obter_sessao
from app.modules.contas.modelos import Usuario
from app.seguranca.tokens import NOME_COOKIE, ler_token


def usuario_atual(request: Request, sessao: Session = Depends(obter_sessao)) -> Usuario:
    token = request.cookies.get(NOME_COOKIE)
    usuario_id = ler_token(token, request.app.state.config.secret_key) if token else None
    usuario = sessao.get(Usuario, usuario_id) if usuario_id else None
    if usuario is None:
        raise HTTPException(status_code=401, detail="Entre na sua conta para continuar.")
    return usuario


def ip_do_cliente(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"
