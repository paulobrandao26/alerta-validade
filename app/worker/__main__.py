"""Inicia o worker como processo separado: python -m app.worker"""

import logging
import signal
import threading

from app.config import obter_configuracao
from app.db.sessao import criar_engine, criar_fabrica
from app.modules.leitura_ia.cliente_ia import criar_leitor
from app.worker.tarefas import rodar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

config = obter_configuracao()
parar = threading.Event()
signal.signal(signal.SIGINT, lambda *_: parar.set())
signal.signal(signal.SIGTERM, lambda *_: parar.set())
rodar(criar_fabrica(criar_engine(config.database_url)), criar_leitor(config), config, parar)
