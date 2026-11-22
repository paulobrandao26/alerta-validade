from datetime import date

import pytest

from app.modules.leitura_ia.schemas import RespostaIAInvalida, data_plausivel, interpretar_resposta

HOJE = date(2026, 11, 22)


def test_le_json_valido():
    r = interpretar_resposta('{"produto": "  Iogurte   natural ", "validade": "2026-12-15", "confianca": 0.92}')
    assert r.produto == "Iogurte natural"
    assert r.validade == date(2026, 12, 15)
    assert r.confianca == 0.92


def test_aceita_json_cercado_de_texto():
    r = interpretar_resposta('Claro! Aqui está:\n```json\n{"produto": null, "validade": null, "confianca": 0}\n```')
    assert r.validade is None and r.confianca == 0


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "não consegui ler",
        '{"produto": "Leite", "validade": "15/12/2026", "confianca": 0.9}',  # data fora do formato combinado
        '{"produto": "Leite", "validade": "2026-12-15", "confianca": 1.7}',  # confiança fora de 0..1
        '{"produto": "Leite", "validade": "2026-12-15"}',  # faltou confiança
        '{"produto": "Leite", "validade": "2026-12-15", "confianca": 0.9',  # JSON quebrado
    ],
)
def test_rejeita_resposta_fora_do_formato(texto):
    with pytest.raises(RespostaIAInvalida):
        interpretar_resposta(texto)


def test_ignora_campos_extras_que_a_ia_inventar():
    r = interpretar_resposta('{"produto": "Queijo", "validade": "2026-12-01", "confianca": 0.8, "lote": "L123"}')
    assert not hasattr(r, "lote")


@pytest.mark.parametrize(
    ("validade", "plausivel"),
    [
        (date(2026, 12, 1), True),
        (date(2026, 1, 1), True),  # vencido há menos de 1 ano
        (date(2024, 1, 1), False),  # provavelmente leu a data de fabricação errada
        (date(2035, 1, 1), False),  # ano lido errado
    ],
)
def test_data_plausivel(validade, plausivel):
    assert data_plausivel(validade, HOJE) is plausivel
