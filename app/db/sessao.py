"""Conexão com o banco. SQLite no computador, PostgreSQL no Docker/produção."""

from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


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
    return create_engine(url, pool_pre_ping=True)


def criar_fabrica(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao(request: Request) -> Iterator[Session]:
    sessao = request.app.state.fabrica_sessao()
    try:
        yield sessao
    finally:
        sessao.close()
