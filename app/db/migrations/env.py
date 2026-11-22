from alembic import context

from app.db.modelos import Base
from app.db.sessao import criar_engine

config = context.config
alvo = Base.metadata


def _url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    from app.config import obter_configuracao

    return obter_configuracao().database_url


def rodar_offline() -> None:
    context.configure(url=_url(), target_metadata=alvo, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def rodar_online() -> None:
    engine = criar_engine(_url())
    with engine.connect() as conexao:
        context.configure(connection=conexao, target_metadata=alvo, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    rodar_offline()
else:
    rodar_online()
