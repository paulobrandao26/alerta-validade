from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.db.sessao import obter_sessao
from app.modules.contas import servico
from app.modules.contas.modelos import Usuario
from app.modules.contas.schemas import AjustesLoja, Cadastro, Conta, Entrada, LojaSaida
from app.seguranca.dependencias import ip_do_cliente, usuario_atual
from app.seguranca.tokens import NOME_COOKIE, criar_token

rotas = APIRouter(prefix="/api/contas", tags=["contas"])


def _conta(request: Request, usuario: Usuario) -> Conta:
    return Conta.model_validate(
        {"usuario": usuario, "loja": usuario.loja, "ia_ligada": request.app.state.config.ia_configurada}
    )


def _abrir_sessao(request: Request, resposta: Response, usuario: Usuario) -> None:
    config = request.app.state.config
    resposta.set_cookie(
        NOME_COOKIE,
        criar_token(usuario.id, config.secret_key, config.sessao_horas),
        max_age=config.sessao_horas * 3600,
        httponly=True,
        secure=config.producao,
        samesite="strict",
        path="/",
    )


@rotas.post("/cadastro", status_code=status.HTTP_201_CREATED, response_model=Conta)
def cadastrar(dados: Cadastro, request: Request, resposta: Response, sessao: Session = Depends(obter_sessao)):
    usuario = servico.cadastrar(sessao, dados)
    _abrir_sessao(request, resposta, usuario)
    return _conta(request, usuario)


@rotas.post("/entrar", response_model=Conta)
def entrar(dados: Entrada, request: Request, resposta: Response, sessao: Session = Depends(obter_sessao)):
    usuario = servico.autenticar(
        sessao, dados.email, dados.senha, ip_do_cliente(request), request.app.state.limitador_login
    )
    if usuario is None:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    _abrir_sessao(request, resposta, usuario)
    return _conta(request, usuario)


@rotas.post("/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair(request: Request):
    resposta = Response(status_code=status.HTTP_204_NO_CONTENT)
    resposta.delete_cookie(
        NOME_COOKIE, path="/", httponly=True, samesite="strict", secure=request.app.state.config.producao
    )
    return resposta


@rotas.get("/eu", response_model=Conta)
def eu(request: Request, usuario: Usuario = Depends(usuario_atual)):
    return _conta(request, usuario)


@rotas.patch("/loja", response_model=LojaSaida)
def ajustar(dados: AjustesLoja, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(obter_sessao)):
    loja = sessao.merge(usuario.loja)
    return servico.ajustar_loja(sessao, loja, dados)
