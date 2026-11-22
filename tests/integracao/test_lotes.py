from concurrent.futures import ThreadPoolExecutor

from tests.conftest import HOJE


def test_cria_lote_e_produto_juntos(logado):
    resposta = logado.post(
        "/api/lotes", json={"produto_nome": "Iogurte Natural", "quantidade": 24, "validade": "2026-11-25"}
    )
    assert resposta.status_code == 201
    lote = resposta.json()
    assert lote["produto_nome"] == "Iogurte Natural"
    assert lote["dias_restantes"] == 3 and lote["estado"] == "atencao"
    assert len(logado.get("/api/produtos").json()) == 1


def test_mesmo_produto_com_nome_digitado_diferente_nao_duplica(logado):
    for nome in ("Leite Integral", "  leite   INTEGRAL "):
        logado.post("/api/lotes", json={"produto_nome": nome, "quantidade": 1, "validade": "2026-12-01"})
    assert len(logado.get("/api/produtos").json()) == 1
    assert len(logado.get("/api/lotes").json()) == 2


def test_lotes_vem_ordenados_pelo_que_vence_primeiro(logado):
    for nome, validade in [("C", "2027-01-10"), ("A", "2026-11-20"), ("B", "2026-11-23")]:
        logado.post("/api/lotes", json={"produto_nome": f"Produto {nome}", "quantidade": 1, "validade": validade})
    lotes = logado.get("/api/lotes").json()
    assert [lote["produto_nome"] for lote in lotes] == ["Produto A", "Produto B", "Produto C"]
    assert [lote["estado"] for lote in lotes] == ["vencido", "atencao", "ok"]


def test_produto_fresco_usa_prazo_padrao(logado):
    resposta = logado.post("/api/lotes", json={"produto_nome": "Pão francês", "quantidade": 50, "prazo_padrao_dias": 2})
    assert resposta.status_code == 201
    assert resposta.json()["validade"] == "2026-11-24" and resposta.json()["origem"] == "prazo"
    # Na próxima entrega, nem precisa informar o prazo: o produto já lembra.
    segunda = logado.post("/api/lotes", json={"produto_nome": "pão francês", "quantidade": 40})
    assert segunda.json()["validade"] == "2026-11-24"


def test_sem_validade_e_sem_prazo_nao_cria_nada(logado):
    resposta = logado.post("/api/lotes", json={"produto_nome": "Queijo", "quantidade": 3})
    assert resposta.status_code == 422
    # A transação desfez tudo: nem o produto ficou gravado.
    assert logado.get("/api/produtos").json() == []


def test_valida_quantidade_e_codigo_de_barras(logado):
    base = {"produto_nome": "Arroz", "validade": "2027-05-01"}
    assert logado.post("/api/lotes", json={**base, "quantidade": 0}).status_code == 422
    assert logado.post("/api/lotes", json={**base, "quantidade": 1, "codigo_barras": "abc"}).status_code == 422
    assert (
        logado.post("/api/lotes", json={**base, "quantidade": 1, "codigo_barras": "7891000100103"}).status_code == 201
    )


def test_baixa_tira_o_lote_da_lista(logado):
    lote = logado.post(
        "/api/lotes", json={"produto_nome": "Presunto", "quantidade": 2, "validade": "2026-11-23"}
    ).json()
    assert logado.post(f"/api/lotes/{lote['id']}/baixa", json={"motivo": "descartado"}).status_code == 204
    assert logado.get("/api/lotes").json() == []
    assert logado.post(f"/api/lotes/{lote['id']}/baixa", json={"motivo": "vendido"}).status_code == 409
    assert logado.post(f"/api/lotes/{lote['id']}/baixa", json={"motivo": "roubado"}).status_code == 422


def test_duas_baixas_ao_mesmo_tempo_so_uma_vale(logado):
    """Dois funcionários tocam em "Vendi" no mesmo lote quase ao mesmo tempo."""
    lote = logado.post(
        "/api/lotes", json={"produto_nome": "Requeijão", "quantidade": 1, "validade": "2026-11-30"}
    ).json()

    def baixar(_):
        return logado.post(f"/api/lotes/{lote['id']}/baixa", json={"motivo": "vendido"}).status_code

    with ThreadPoolExecutor(max_workers=6) as grupo:
        codigos = list(grupo.map(baixar, range(6)))
    assert codigos.count(204) == 1
    assert codigos.count(409) == 5


def test_busca_de_produto_nao_quebra_com_caracteres_especiais(logado):
    logado.post("/api/lotes", json={"produto_nome": "Suco 100% uva", "quantidade": 1, "validade": "2026-12-10"})
    logado.post("/api/lotes", json={"produto_nome": "Suco de laranja", "quantidade": 1, "validade": "2026-12-10"})
    assert [p["nome"] for p in logado.get("/api/produtos", params={"busca": "100%"}).json()] == ["Suco 100% uva"]
    assert len(logado.get("/api/produtos", params={"busca": "suco"}).json()) == 2
    assert logado.get("/api/produtos", params={"busca": "'; DROP TABLE produtos; --"}).status_code == 200
    assert len(logado.get("/api/produtos").json()) == 2


def test_hoje_dos_testes_esta_fixo():
    assert HOJE.isoformat() == "2026-11-22"
