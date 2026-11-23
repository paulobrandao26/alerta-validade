"""Monta a aplicação: API, proteções, worker e a interface (PWA)."""

import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Configuracao, obter_configuracao
from app.db.sessao import criar_engine, criar_fabrica
from app.modules.alertas.rotas import rotas as rotas_alertas
from app.modules.contas.rotas import rotas as rotas_contas
from app.modules.leitura_ia.cliente_ia import LeitorDeEmbalagem, criar_leitor
from app.modules.leitura_ia.rotas import rotas as rotas_leituras
from app.modules.produtos.rotas import rotas as rotas_produtos
from app.nucleo.erros import ErroDeNegocio
from app.seguranca.limitador import Limitador
from app.seguranca.protecoes import BloqueioCSRF, CabecalhosDeSeguranca
from app.worker.tarefas import iniciar_em_segundo_plano

PASTA_INTERFACE = Path(__file__).resolve().parent.parent / "frontend"
# O Windows não conhece alguns tipos; sem isso o navegador recebe text/plain.
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")
log = logging.getLogger("validade")


def migrar(url: str) -> None:
    from alembic import command
    from alembic.config import Config

    raiz = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(raiz / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(raiz / "app" / "db" / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")


def criar_app(config: Configuracao | None = None, leitor: LeitorDeEmbalagem | None = None) -> FastAPI:
    config = config or obter_configuracao()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        if config.migrar_ao_iniciar:
            migrar(config.database_url)
        parar = None
        if config.worker_embutido:
            parar = iniciar_em_segundo_plano(app.state.fabrica_sessao, app.state.leitor, config)
        yield
        if parar:
            parar.set()

    app = FastAPI(
        title="Validade Certa",
        version="0.1.0",
        lifespan=ciclo_de_vida,
        docs_url=None if config.producao else "/api/docs",
        redoc_url=None,
        openapi_url=None if config.producao else "/api/openapi.json",
    )
    engine = criar_engine(config.database_url)
    app.state.config = config
    app.state.engine = engine
    app.state.fabrica_sessao = criar_fabrica(engine)
    app.state.leitor = leitor or criar_leitor(config)
    app.state.limitador_login = Limitador(config.login_max_tentativas, config.login_janela_segundos)
    app.state.limitador_fotos = Limitador(config.fotos_por_minuto, 60)

    app.add_middleware(BloqueioCSRF)
    app.add_middleware(CabecalhosDeSeguranca, producao=config.producao)

    @app.exception_handler(ErroDeNegocio)
    async def _erro_de_negocio(_: Request, erro: ErroDeNegocio):
        return JSONResponse({"detail": erro.mensagem}, status_code=erro.status_http)

    @app.exception_handler(RequestValidationError)
    async def _dados_invalidos(_: Request, erro: RequestValidationError):
        campos = []
        for item in erro.errors():
            campo = ".".join(str(p) for p in item.get("loc", ())[1:]) or "dados"
            campos.append({"campo": campo, "mensagem": item.get("msg", "inválido")})
        return JSONResponse({"detail": "Confira os dados enviados.", "campos": campos}, status_code=422)

    @app.exception_handler(Exception)
    async def _erro_inesperado(_: Request, erro: Exception):
        log.exception("Erro inesperado", exc_info=erro)
        return JSONResponse({"detail": "Erro interno. Tente de novo."}, status_code=500)

    for rotas in (rotas_contas, rotas_produtos, rotas_leituras, rotas_alertas):
        app.include_router(rotas)

    @app.get("/api/saude", tags=["sistema"])
    def saude():
        # Consulta o banco de verdade: serve para monitorar e mantém o banco acordado.
        try:
            with app.state.engine.connect() as conexao:
                conexao.execute(text("SELECT 1"))
            banco = "ok"
        except Exception:
            log.exception("Banco fora do ar")
            return JSONResponse({"status": "erro", "banco": "fora do ar"}, status_code=503)
        return {"status": "ok", "banco": banco, "ia": "ligada" if config.ia_configurada else "desligada"}

    @app.api_route("/api/{caminho:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def api_inexistente(caminho: str):
        raise StarletteHTTPException(status_code=404, detail="Rota não encontrada.")

    # O service worker precisa ser servido da raiz para controlar o app todo.
    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return FileResponse(
            PASTA_INTERFACE / "sw.js",
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
        )

    if PASTA_INTERFACE.is_dir():
        app.mount("/", StaticFiles(directory=PASTA_INTERFACE, html=True), name="interface")
    return app
