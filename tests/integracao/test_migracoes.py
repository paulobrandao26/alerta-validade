"""As migrations precisam criar exatamente o que os modelos descrevem."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.db.modelos import Base
from app.main import migrar


def test_migrations_batem_com_os_modelos(tmp_path):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    migrar(url)
    engine = create_engine(url)
    with engine.connect() as conexao:
        diferencas = compare_metadata(MigrationContext.configure(conexao), Base.metadata)
    engine.dispose()
    assert diferencas == [], f"Falta uma migration: {diferencas}"
