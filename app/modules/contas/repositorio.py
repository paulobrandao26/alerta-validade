from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.contas.modelos import Loja, Usuario


def buscar_por_email(sessao: Session, email: str) -> Usuario | None:
    return sessao.scalar(select(Usuario).where(Usuario.email == email))


def criar_loja_com_dono(sessao: Session, nome_loja: str, email: str, senha_hash: str) -> Usuario:
    loja = Loja(nome=nome_loja)
    usuario = Usuario(loja=loja, email=email, senha_hash=senha_hash)
    sessao.add_all([loja, usuario])
    sessao.flush()
    return usuario
