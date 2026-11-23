import pytest

from app.config import Configuracao
from app.seguranca import senhas
from app.seguranca.limitador import Limitador
from app.seguranca.tokens import criar_token, ler_token

CHAVE = "k" * 48


def test_senha_guardada_com_hash_e_conferida():
    h = senhas.gerar_hash("minha-senha-1")
    assert "minha-senha-1" not in h and h.startswith("$argon2")
    assert senhas.conferir("minha-senha-1", h)
    assert not senhas.conferir("outra-senha", h)


def test_conferir_sem_usuario_sempre_falha():
    assert not senhas.conferir("senha-que-ninguem-usa", None)


def test_token_valido_e_adulterado():
    token = criar_token(42, CHAVE, horas=1)
    assert ler_token(token, CHAVE) == 42
    assert ler_token(token, "outra-chave-" + "z" * 40) is None
    assert ler_token(token[:-2] + "xx", CHAVE) is None
    assert ler_token("lixo", CHAVE) is None


def test_token_vencido_e_recusado():
    assert ler_token(criar_token(1, CHAVE, horas=-1), CHAVE) is None


def test_limitador_bloqueia_e_libera_depois_da_janela():
    agora = [0.0]
    limite = Limitador(maximo=3, janela_segundos=60, relogio=lambda: agora[0])
    assert all(limite.tentar("ip") for _ in range(3))
    assert not limite.tentar("ip")
    assert limite.tentar("outro-ip")  # chaves diferentes não se misturam
    agora[0] = 61
    assert limite.tentar("ip")


def test_producao_exige_chave_secreta_forte():
    with pytest.raises(ValueError):
        Configuracao(_env_file=None, ambiente="producao", secret_key="curta")
    with pytest.raises(ValueError):
        Configuracao(_env_file=None, ambiente="producao", secret_key="")


def test_desenvolvimento_gera_chave_aleatoria():
    a = Configuracao(_env_file=None, ambiente="desenvolvimento", secret_key="")
    b = Configuracao(_env_file=None, ambiente="desenvolvimento", secret_key="")
    assert len(a.secret_key) >= 32 and a.secret_key != b.secret_key


def test_endereco_do_supabase_usa_o_driver_instalado():
    from app.config import Configuracao

    for url in ("postgresql://u:s@h:6543/postgres", "postgres://u:s@h:6543/postgres"):
        config = Configuracao(_env_file=None, database_url=url)
        assert config.database_url == "postgresql+psycopg://u:s@h:6543/postgres"


def test_dependencias_iguais_no_requirements_e_no_pyproject():
    """O Vercel instala pelo pyproject.toml e o Docker pelo requirements.txt."""
    import tomllib
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    requirements = {
        linha.strip()
        for linha in (raiz / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if linha.strip() and not linha.startswith("#")
    }
    pyproject = set(tomllib.loads((raiz / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"])
    assert requirements == pyproject
