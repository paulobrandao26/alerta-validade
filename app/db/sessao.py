"""Conexão com o banco. SQLite no computador, PostgreSQL no Docker/produção."""

from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool


def criar_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        caminho = url.split("///", 1)[-1]
        if caminho and caminho != ":memory:":
            Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})

        @event.listens_for(engine, "connect")
        def _ligar_chaves_estrangeiras(conexao, _registro):
            cursor = conexao.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        return engine
    if ":6543/" in url:
        # Pooler do Supabase em modo transação (usado em hospedagem que "dorme", como o Vercel):
        # o próprio pooler guarda as conexões, então aqui não se mantém nenhuma aberta,
        # e comandos preparados ficam desligados porque esse modo não os suporta.
        return create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
    return create_engine(url, pool_pre_ping=True)


def criar_fabrica(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao(request: Request) -> Iterator[Session]:
    sessao = request.app.state.fabrica_sessao()
    try:
        yield sessao
    finally:
        sessao.close()
