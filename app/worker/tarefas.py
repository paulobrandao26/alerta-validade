"""Worker: processa a fila de fotos fora das requisições da API.

Roda de dois jeitos:
- embutido no servidor (WORKER_EMBUTIDO=true, prático no computador);
- como processo separado: `python -m app.worker` (é assim no Docker).
"""

import logging
import threading

from sqlalchemy.orm import Session, sessionmaker

from app.config import Configuracao
from app.modules.leitura_ia import servico
from app.modules.leitura_ia.cliente_ia import LeitorDeEmbalagem
from app.nucleo import relogio

log = logging.getLogger("validade.worker")


def processar_fila(
    fabrica: sessionmaker[Session], leitor: LeitorDeEmbalagem, config: Configuracao, limite: int = 20
) -> int:
    """Processa até `limite` fotos da fila. Devolve quantas processou."""
    feitas = 0
    with fabrica() as sessao:
        while feitas < limite:
            leitura = servico.reivindicar_proxima(sessao)
            if leitura is None:
                break
            servico.processar(
                sessao,
                leitura,
                leitor,
                config.pasta_uploads,
                relogio.hoje(config.fuso_horas),
                config.ia_confianca_minima,
                config.leitura_max_tentativas,
            )
            feitas += 1
    return feitas


def rodar(fabrica, leitor, config: Configuracao, parar: threading.Event) -> None:
    log.info("Worker iniciado (IA %s).", "ligada" if config.ia_configurada else "desligada")
    while not parar.is_set():
        try:
            processar_fila(fabrica, leitor, config)
        except Exception:  # o worker não pode morrer por causa de um erro
            log.exception("Erro no ciclo do worker")
        parar.wait(config.worker_intervalo_segundos)
    log.info("Worker parado.")


def iniciar_em_segundo_plano(fabrica, leitor, config: Configuracao) -> threading.Event:
    parar = threading.Event()
    threading.Thread(target=rodar, args=(fabrica, leitor, config, parar), name="worker-fotos", daemon=True).start()
    return parar
