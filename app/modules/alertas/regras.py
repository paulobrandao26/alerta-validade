"""Regra central: em que situação está um lote, olhando a validade."""

from datetime import date
from enum import StrEnum


class Estado(StrEnum):
    VENCIDO = "vencido"
    ATENCAO = "atencao"
    OK = "ok"


def dias_restantes(validade: date, hoje: date) -> int:
    return (validade - hoje).days


def classificar(validade: date, hoje: date, dias_alerta: int) -> Estado:
    """Vencido: a data já passou. Atenção: vence dentro do prazo de alerta da loja.

    O produto ainda pode ser vendido no próprio dia da validade, por isso
    "vence hoje" (0 dias) é atenção e não vencido.
    """
    restam = dias_restantes(validade, hoje)
    if restam < 0:
        return Estado.VENCIDO
    if restam <= dias_alerta:
        return Estado.ATENCAO
    return Estado.OK
