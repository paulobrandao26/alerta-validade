"""Acesso ao banco. Toda consulta filtra pela loja: uma loja nunca enxerga dados de outra."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.produtos.modelos import Lote, Produto, Situacao


def chave_do_nome(nome: str) -> str:
    return " ".join(nome.split()).casefold()


def buscar_produto_por_nome(sessao: Session, loja_id: int, nome: str) -> Produto | None:
    return sessao.scalar(select(Produto).where(Produto.loja_id == loja_id, Produto.nome_chave == chave_do_nome(nome)))


def listar_produtos(sessao: Session, loja_id: int, busca: str | None = None, limite: int = 50) -> list[Produto]:
    consulta = select(Produto).where(Produto.loja_id == loja_id)
    if busca:
        termo = chave_do_nome(busca).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        consulta = consulta.where(Produto.nome_chave.like(f"%{termo}%", escape="\\"))
    return list(sessao.scalars(consulta.order_by(Produto.nome).limit(limite)))


def buscar_lote(sessao: Session, loja_id: int, lote_id: int) -> Lote | None:
    return sessao.scalar(select(Lote).where(Lote.id == lote_id, Lote.loja_id == loja_id))


def listar_lotes_ativos(sessao: Session, loja_id: int) -> list[Lote]:
    return list(
        sessao.scalars(
            select(Lote)
            .where(Lote.loja_id == loja_id, Lote.situacao == Situacao.ATIVO)
            .order_by(Lote.validade, Lote.id)
        )
    )
