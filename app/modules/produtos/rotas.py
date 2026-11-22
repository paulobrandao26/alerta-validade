from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.sessao import obter_sessao
from app.modules.contas.modelos import Usuario
from app.modules.produtos import repositorio, servico
from app.modules.produtos.schemas import Baixa, LoteSaida, NovoLote, ProdutoSaida
from app.nucleo import relogio
from app.seguranca.dependencias import usuario_atual

rotas = APIRouter(prefix="/api", tags=["produtos"])


def _hoje(request: Request):
    return relogio.hoje(request.app.state.config.fuso_horas)


@rotas.get("/produtos", response_model=list[ProdutoSaida])
def listar_produtos(
    busca: str | None = Query(default=None, max_length=60),
    usuario: Usuario = Depends(usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    return repositorio.listar_produtos(sessao, usuario.loja_id, busca)


@rotas.get("/lotes", response_model=list[LoteSaida])
def listar_lotes(request: Request, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(obter_sessao)):
    hoje = _hoje(request)
    dias = usuario.loja.dias_alerta
    return [servico.para_saida(lote, hoje, dias) for lote in repositorio.listar_lotes_ativos(sessao, usuario.loja_id)]


@rotas.post("/lotes", response_model=LoteSaida, status_code=status.HTTP_201_CREATED)
def criar_lote(
    dados: NovoLote,
    request: Request,
    usuario: Usuario = Depends(usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    hoje = _hoje(request)
    lote = servico.criar_lote(sessao, usuario.loja_id, dados, hoje)
    sessao.commit()
    return servico.para_saida(lote, hoje, usuario.loja.dias_alerta)


@rotas.post("/lotes/{lote_id}/baixa", status_code=status.HTTP_204_NO_CONTENT)
def dar_baixa(
    lote_id: int, dados: Baixa, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(obter_sessao)
):
    servico.dar_baixa(sessao, usuario.loja_id, lote_id, dados.motivo)
