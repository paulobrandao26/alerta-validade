from datetime import date, timedelta

import pytest

from app.modules.alertas.regras import Estado, classificar, dias_restantes

HOJE = date(2026, 11, 22)


@pytest.mark.parametrize(
    ("dias", "esperado"),
    [
        (-30, Estado.VENCIDO),
        (-1, Estado.VENCIDO),
        (0, Estado.ATENCAO),  # vence hoje: ainda pode vender, mas é prioridade
        (7, Estado.ATENCAO),  # limite do alerta entra no alerta
        (8, Estado.OK),
        (400, Estado.OK),
    ],
)
def test_classifica_pela_distancia_da_validade(dias, esperado):
    assert classificar(HOJE + timedelta(days=dias), HOJE, dias_alerta=7) == esperado


def test_prazo_de_alerta_da_loja_muda_a_classificacao():
    validade = HOJE + timedelta(days=10)
    assert classificar(validade, HOJE, dias_alerta=7) == Estado.OK
    assert classificar(validade, HOJE, dias_alerta=15) == Estado.ATENCAO


def test_dias_restantes_atravessa_virada_de_ano():
    assert dias_restantes(date(2027, 1, 2), date(2026, 12, 30)) == 3
