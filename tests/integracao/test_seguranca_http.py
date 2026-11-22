from fastapi.testclient import TestClient

from app.config import Configuracao
from app.main import criar_app
from tests.conftest import SENHA


def test_sem_cabecalho_csrf_nada_e_alterado(app):
    cliente = TestClient(app)  # cliente "de fora", sem o cabeçalho do nosso app
    resposta = cliente.post("/api/contas/cadastro", json={"nome_loja": "Loja", "email": "a@b.com", "senha": SENHA})
    assert resposta.status_code == 403
    assert cliente.post("/api/contas/sair").status_code == 403


def test_leitura_nao_precisa_de_cabecalho_csrf(app):
    assert TestClient(app).get("/api/saude").status_code == 200


def test_cabecalhos_de_seguranca(logado):
    for rota in ("/api/saude", "/", "/api/contas/eu"):
        h = logado.get(rota).headers
        assert "default-src 'self'" in h["content-security-policy"]
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "no-referrer"
    assert logado.get("/api/contas/eu").headers["cache-control"] == "no-store"


def test_erro_inesperado_nao_vaza_detalhes(app, logado, monkeypatch):
    from app.modules.produtos import repositorio

    def explode(*_a, **_k):
        raise RuntimeError("senha do banco: hunter2")

    monkeypatch.setattr(repositorio, "listar_lotes_ativos", explode)
    cliente = TestClient(app, raise_server_exceptions=False)
    cliente.cookies = logado.cookies
    resposta = cliente.get("/api/lotes")
    assert resposta.status_code == 500
    assert "hunter2" not in resposta.text and "Traceback" not in resposta.text


def test_rota_de_api_inexistente_da_404_em_json(logado):
    resposta = logado.get("/api/nao-existe")
    assert resposta.status_code == 404 and resposta.headers["content-type"].startswith("application/json")


def test_producao_esconde_documentacao_e_usa_cookie_seguro(tmp_path):
    config = Configuracao(
        _env_file=None,
        ambiente="producao",
        secret_key="p" * 48,
        database_url=f"sqlite:///{(tmp_path / 'p.db').as_posix()}",
        migrar_ao_iniciar=True,
        worker_embutido=False,
        pasta_uploads=str(tmp_path / "f"),
    )
    with TestClient(criar_app(config)) as cliente:
        cliente.headers["X-Requested-With"] = "validade-certa"
        assert cliente.get("/api/docs").status_code == 404
        assert cliente.get("/api/openapi.json").status_code == 404
        assert "max-age" in cliente.get("/api/saude").headers["strict-transport-security"]
        resposta = cliente.post("/api/contas/cadastro", json={"nome_loja": "Loja", "email": "a@b.com", "senha": SENHA})
        cookie = resposta.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie


def test_interface_e_service_worker_sao_servidos(logado):
    assert logado.get("/").status_code == 200
    sw = logado.get("/sw.js")
    assert sw.status_code == 200 and "javascript" in sw.headers["content-type"]
    assert logado.get("/manifest.webmanifest").status_code == 200
