from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import Configuracao
from app.db import modelos  # noqa: F401  (registra as tabelas)
from app.db.base import Base
from app.main import criar_app
from app.modules.leitura_ia.schemas import RespostaIA
from app.nucleo import relogio
from app.seguranca.protecoes import CABECALHO_CSRF, VALOR_CSRF
from app.worker.tarefas import processar_fila

HOJE = date(2026, 11, 22)
SENHA = "senha-forte-123"


class LeitorFalso:
    """Faz o papel da IA nos testes: devolve respostas ou erros programados."""

    def __init__(self):
        self.respostas: list = []
        self.chamadas = 0

    def programar(self, *respostas):
        self.respostas = list(respostas)

    def ler(self, imagem: bytes, mime: str) -> RespostaIA:
        self.chamadas += 1
        resposta = self.respostas.pop(0) if self.respostas else RespostaIA(confianca=0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


@pytest.fixture
def config(tmp_path):
    return Configuracao(
        _env_file=None,
        ambiente="teste",
        database_url=f"sqlite:///{(tmp_path / 'teste.db').as_posix()}",
        migrar_ao_iniciar=False,
        worker_embutido=False,
        secret_key="chave-de-teste-" + "x" * 40,
        pasta_uploads=str(tmp_path / "fotos"),
        gemini_api_key="",
        groq_api_key="",
        ollama_url="",
        upload_max_bytes=200_000,
    )


@pytest.fixture
def leitor():
    return LeitorFalso()


@pytest.fixture
def app(config, leitor, monkeypatch):
    monkeypatch.setattr(relogio, "hoje", lambda *_: HOJE)
    aplicacao = criar_app(config, leitor=leitor)
    Base.metadata.create_all(aplicacao.state.engine)
    yield aplicacao
    aplicacao.state.engine.dispose()


def _cliente(app) -> TestClient:
    cliente = TestClient(app)
    cliente.headers[CABECALHO_CSRF] = VALOR_CSRF
    return cliente


@pytest.fixture
def novo_cliente(app):
    """Fábrica de clientes (cada um com seus cookies, como navegadores diferentes)."""
    return lambda: _cliente(app)


def cadastrar(cliente: TestClient, email: str = "dono@mercado.com", loja: str = "Mercadinho Boa Vista"):
    resposta = cliente.post("/api/contas/cadastro", json={"nome_loja": loja, "email": email, "senha": SENHA})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.fixture
def logado(novo_cliente):
    cliente = novo_cliente()
    cadastrar(cliente)
    return cliente


@pytest.fixture
def rodar_worker(app, leitor, config):
    return lambda: processar_fila(app.state.fabrica_sessao, leitor, config)


# Menor JPEG válido o bastante para passar na checagem de assinatura.
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"\xff\xd9"
