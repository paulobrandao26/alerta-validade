"""Limite de tentativas em uma janela de tempo (ex.: login, envio de fotos).

Fica na memória do processo: serve para um servidor só. Com vários servidores,
o certo é guardar a contagem no Redis (ver docs/limitacoes.md).
"""

import threading
import time
from collections import defaultdict, deque


class Limitador:
    def __init__(self, maximo: int, janela_segundos: float, relogio=time.monotonic):
        self.maximo = maximo
        self.janela = janela_segundos
        self._relogio = relogio
        self._registros: dict[str, deque[float]] = defaultdict(deque)
        self._trava = threading.Lock()

    def _limpar(self, chave: str, agora: float) -> deque[float]:
        fila = self._registros[chave]
        while fila and agora - fila[0] >= self.janela:
            fila.popleft()
        return fila

    def bloqueado(self, chave: str) -> bool:
        with self._trava:
            return len(self._limpar(chave, self._relogio())) >= self.maximo

    def registrar(self, chave: str) -> None:
        with self._trava:
            agora = self._relogio()
            self._limpar(chave, agora).append(agora)

    def tentar(self, chave: str) -> bool:
        """Registra uma tentativa; devolve False se passou do limite."""
        with self._trava:
            agora = self._relogio()
            fila = self._limpar(chave, agora)
            if len(fila) >= self.maximo:
                return False
            fila.append(agora)
            return True

    def zerar(self, chave: str) -> None:
        with self._trava:
            self._registros.pop(chave, None)
