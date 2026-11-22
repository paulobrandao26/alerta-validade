from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.sessao import obter_sessao
from app.modules.alertas.servico import Resumo, resumir
from app.modules.contas.modelos import Usuario
from app.nucleo import relogio
from app.seguranca.dependencias import usuario_atual

rotas = APIRouter(prefix="/api/alertas", tags=["alertas"])


@rotas.get("/resumo", response_model=Resumo)
def resumo(request: Request, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(obter_sessao)):
    return resumir(sessao, usuario.loja, relogio.hoje(request.app.state.config.fuso_horas))
