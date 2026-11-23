"""Regras da leitura por foto e da fila que alimenta o worker."""

import logging
from datetime import date, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.leitura_ia.arquivos import caminho_seguro
from app.modules.leitura_ia.cliente_ia import IAIndisponivel, IANaoConfigurada, LeitorDeEmbalagem
from app.modules.leitura_ia.modelos import Leitura, StatusLeitura
from app.modules.leitura_ia.schemas import Confirmacao, RespostaIAInvalida, data_plausivel
from app.modules.produtos.modelos import Origem
from app.modules.produtos.schemas import NovoLote
from app.modules.produtos.servico import criar_lote
from app.nucleo.erros import Conflito, NaoEncontrado
from app.nucleo.relogio import agora_utc

log = logging.getLogger("validade.leitura")

# Uma leitura presa em "processando" por mais que isso (worker caiu no meio) volta para a fila.
TEMPO_MAXIMO_PROCESSANDO = timedelta(minutes=5)


def registrar(sessao: Session, loja_id: int, usuario_id: int, arquivo: str, mime: str) -> Leitura:
    leitura = Leitura(loja_id=loja_id, usuario_id=usuario_id, arquivo=arquivo, mime=mime)
    sessao.add(leitura)
    sessao.commit()
    return leitura


def buscar(sessao: Session, loja_id: int, leitura_id: int) -> Leitura:
    leitura = sessao.scalar(select(Leitura).where(Leitura.id == leitura_id, Leitura.loja_id == loja_id))
    if leitura is None:
        raise NaoEncontrado("Leitura não encontrada.")
    return leitura


def reivindicar_proxima(sessao: Session) -> Leitura | None:
    """Pega a próxima foto da fila de forma atômica.

    O UPDATE só muda o status se ele ainda for "pendente". Se dois workers
    tentarem pegar a mesma foto, só um consegue (rowcount == 1).
    """
    agora = agora_utc()
    sessao.execute(
        update(Leitura)
        .where(
            Leitura.status == StatusLeitura.PROCESSANDO,
            Leitura.atualizado_em < agora - TEMPO_MAXIMO_PROCESSANDO,
        )
        .values(status=StatusLeitura.PENDENTE, atualizado_em=agora)
        .execution_options(synchronize_session=False)
    )
    sessao.commit()

    candidatos = sessao.scalars(
        select(Leitura.id)
        .where(Leitura.status == StatusLeitura.PENDENTE, Leitura.proxima_tentativa_em <= agora)
        .order_by(Leitura.proxima_tentativa_em, Leitura.id)
        .limit(5)
    ).all()
    for leitura_id in candidatos:
        resultado = sessao.execute(
            update(Leitura)
            .where(Leitura.id == leitura_id, Leitura.status == StatusLeitura.PENDENTE)
            .values(status=StatusLeitura.PROCESSANDO, atualizado_em=agora)
            .execution_options(synchronize_session=False)
        )
        sessao.commit()
        if resultado.rowcount == 1:
            return sessao.get(Leitura, leitura_id, populate_existing=True)
    return None


def processar(
    sessao: Session,
    leitura: Leitura,
    leitor: LeitorDeEmbalagem,
    pasta_uploads: str,
    hoje: date,
    confianca_minima: float,
    max_tentativas: int,
    imagem: bytes | None = None,
) -> None:
    """Chama a IA para uma leitura e grava o resultado.

    Nenhuma falha da IA perde a foto: ou ela volta para a fila (falha passageira),
    ou vai para revisão manual, onde a pessoa digita os dados.
    Com `imagem`, a foto vem da memória (leitura imediata) e não existe arquivo em disco.
    """
    leitura.tentativas += 1
    try:
        if imagem is None:
            imagem = caminho_seguro(pasta_uploads, leitura.arquivo).read_bytes()
        resposta = leitor.ler(imagem, leitura.mime)
    except IANaoConfigurada:
        _para_revisao(leitura, "Leitura automática desligada. Preencha os dados.")
    except IAIndisponivel as erro:
        if leitura.tentativas >= max_tentativas:
            _para_revisao(leitura, "A IA não respondeu. Preencha os dados.")
        else:
            espera = timedelta(seconds=30 * 2 ** (leitura.tentativas - 1))
            leitura.status = StatusLeitura.PENDENTE
            leitura.proxima_tentativa_em = agora_utc() + espera
            leitura.erro = "IA fora do ar, tentando de novo."
        log.warning("IA indisponível na leitura %s: %s", leitura.id, erro)
    except RespostaIAInvalida:
        _para_revisao(leitura, "Não consegui ler a foto. Preencha os dados.")
    except FileNotFoundError:
        _para_revisao(leitura, "A foto não foi encontrada. Preencha os dados.")
    except Exception:  # nunca deixar a leitura presa por um erro inesperado
        log.exception("Erro inesperado na leitura %s", leitura.id)
        _para_revisao(leitura, "Erro ao ler a foto. Preencha os dados.")
    else:
        leitura.produto_lido = resposta.produto
        leitura.validade_lida = resposta.validade
        leitura.confianca = resposta.confianca
        confiavel = (
            resposta.validade is not None
            and resposta.confianca >= confianca_minima
            and data_plausivel(resposta.validade, hoje)
        )
        if confiavel:
            leitura.status = StatusLeitura.LIDA
            leitura.erro = None
        else:
            _para_revisao(leitura, "A data não ficou clara. Confira antes de salvar.")
    sessao.commit()
    # Terminou a leitura (com ou sem sucesso): a foto não é mais necessária no servidor.
    # A pessoa confere olhando a foto que ficou no próprio celular. Sem custo de armazenamento.
    if leitura.status != StatusLeitura.PENDENTE and leitura.arquivo:
        apagar_foto(pasta_uploads, leitura.arquivo)


def apagar_foto(pasta_uploads: str, arquivo: str) -> None:
    try:
        caminho_seguro(pasta_uploads, arquivo).unlink(missing_ok=True)
    except Exception:  # apagar é limpeza: nunca derruba a leitura
        log.warning("Não consegui apagar a foto %s", arquivo)


def _para_revisao(leitura: Leitura, motivo: str) -> None:
    leitura.status = StatusLeitura.REVISAO
    leitura.erro = motivo


def confirmar(sessao: Session, loja_id: int, leitura_id: int, dados: Confirmacao, hoje: date):
    """A pessoa confere os dados e a leitura vira um lote (na mesma transação)."""
    leitura = buscar(sessao, loja_id, leitura_id)
    if leitura.status not in (StatusLeitura.LIDA, StatusLeitura.REVISAO):
        raise Conflito("Essa foto ainda está sendo lida ou já foi salva.")
    lote = criar_lote(
        sessao,
        loja_id,
        NovoLote(produto_nome=dados.produto_nome, quantidade=dados.quantidade, validade=dados.validade),
        hoje,
        origem=Origem.FOTO,
    )
    resultado = sessao.execute(
        update(Leitura)
        .where(
            Leitura.id == leitura.id,
            Leitura.status.in_([StatusLeitura.LIDA, StatusLeitura.REVISAO]),
        )
        .values(status=StatusLeitura.CONFIRMADA, lote_id=lote.id, atualizado_em=agora_utc())
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:  # duas confirmações ao mesmo tempo: só uma vale
        sessao.rollback()
        raise Conflito("Essa foto já foi salva.")
    sessao.commit()
    return lote
