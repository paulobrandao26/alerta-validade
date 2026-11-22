from datetime import date, timedelta

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.alertas.regras import classificar, dias_restantes
from app.modules.produtos import repositorio
from app.modules.produtos.modelos import Lote, Origem, Produto, Situacao
from app.modules.produtos.schemas import LoteSaida, NovoLote
from app.nucleo.erros import Conflito, DadosInvalidos, NaoEncontrado
from app.nucleo.relogio import agora_utc


def obter_ou_criar_produto(
    sessao: Session, loja_id: int, nome: str, codigo_barras: str | None = None, prazo: int | None = None
) -> Produto:
    produto = repositorio.buscar_produto_por_nome(sessao, loja_id, nome)
    if produto:
        if codigo_barras and not produto.codigo_barras:
            produto.codigo_barras = codigo_barras
        return produto
    produto = Produto(
        loja_id=loja_id,
        nome=nome,
        nome_chave=repositorio.chave_do_nome(nome),
        codigo_barras=codigo_barras,
        prazo_padrao_dias=prazo,
    )
    sessao.add(produto)
    try:
        with sessao.begin_nested():  # outro pedido pode ter criado o mesmo produto agora
            sessao.flush()
    except IntegrityError:
        produto = repositorio.buscar_produto_por_nome(sessao, loja_id, nome)
        if produto is None:
            raise
    return produto


def criar_lote(sessao: Session, loja_id: int, dados: NovoLote, hoje: date, origem: Origem = Origem.MANUAL) -> Lote:
    """Cria o lote e o produto (se for novo) numa transação só: ou grava tudo, ou nada."""
    try:
        produto = obter_ou_criar_produto(
            sessao, loja_id, dados.produto_nome, dados.codigo_barras, dados.prazo_padrao_dias
        )
        validade = dados.validade
        if validade is None:
            if not produto.prazo_padrao_dias:
                raise DadosInvalidos("Informe a validade (ou um prazo em dias para produtos frescos).")
            validade = hoje + timedelta(days=produto.prazo_padrao_dias)
            origem = Origem.PRAZO
        lote = Lote(
            loja_id=loja_id,
            produto_id=produto.id,
            quantidade=dados.quantidade,
            validade=validade,
            origem=origem,
        )
        sessao.add(lote)
        sessao.flush()
    except Exception:
        sessao.rollback()
        raise
    return lote


def dar_baixa(sessao: Session, loja_id: int, lote_id: int, motivo: str) -> None:
    """Marca o lote como vendido ou descartado.

    O UPDATE só acontece se o lote ainda estiver ativo: se duas pessoas tocarem
    em "Vendi" ao mesmo tempo, só uma baixa vale e a outra recebe 409.
    """
    if repositorio.buscar_lote(sessao, loja_id, lote_id) is None:
        raise NaoEncontrado("Lote não encontrado.")
    resultado = sessao.execute(
        update(Lote)
        .where(Lote.id == lote_id, Lote.loja_id == loja_id, Lote.situacao == Situacao.ATIVO)
        .values(situacao=motivo, baixado_em=agora_utc())
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:
        sessao.rollback()
        raise Conflito("Esse lote já foi baixado.")
    sessao.commit()


def para_saida(lote: Lote, hoje: date, dias_alerta: int) -> LoteSaida:
    return LoteSaida(
        id=lote.id,
        produto_id=lote.produto_id,
        produto_nome=lote.produto.nome,
        quantidade=lote.quantidade,
        validade=lote.validade,
        dias_restantes=dias_restantes(lote.validade, hoje),
        estado=classificar(lote.validade, hoje, dias_alerta),
        situacao=lote.situacao,
        origem=lote.origem,
    )
