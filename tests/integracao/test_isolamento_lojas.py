"""Uma loja nunca pode ver ou mexer nos dados de outra, mesmo adivinhando os ids."""

from tests.conftest import JPEG, cadastrar


def test_loja_nao_ve_nem_mexe_no_que_e_da_outra(novo_cliente):
    loja_a = novo_cliente()
    cadastrar(loja_a, email="a@mercado.com", loja="Mercado A")
    loja_b = novo_cliente()
    cadastrar(loja_b, email="b@mercado.com", loja="Mercado B")

    lote = loja_a.post("/api/lotes", json={"produto_nome": "Leite", "quantidade": 5, "validade": "2026-11-25"}).json()
    leitura = loja_a.post("/api/leituras", files={"foto": ("f.jpg", JPEG, "image/jpeg")}).json()

    assert loja_b.get("/api/lotes").json() == []
    assert loja_b.get("/api/produtos").json() == []
    assert loja_b.get("/api/alertas/resumo").json()["atencao"] == 0

    assert loja_b.post(f"/api/lotes/{lote['id']}/baixa", json={"motivo": "vendido"}).status_code == 404
    assert loja_b.get(f"/api/leituras/{leitura['id']}").status_code == 404
    confirmar = loja_b.post(
        f"/api/leituras/{leitura['id']}/confirmar",
        json={"produto_nome": "Leite", "validade": "2026-11-25", "quantidade": 1},
    )
    assert confirmar.status_code == 404

    # E a loja A continua com tudo intacto.
    assert len(loja_a.get("/api/lotes").json()) == 1


def test_mesmo_nome_de_produto_em_lojas_diferentes(novo_cliente):
    for email in ("a@m.com", "b@m.com"):
        cliente = novo_cliente()
        cadastrar(cliente, email=email)
        assert (
            cliente.post(
                "/api/lotes", json={"produto_nome": "Leite", "quantidade": 1, "validade": "2026-12-01"}
            ).status_code
            == 201
        )


def test_sem_login_nada_e_acessivel(novo_cliente):
    cliente = novo_cliente()
    for metodo, rota in [
        ("get", "/api/lotes"),
        ("get", "/api/produtos"),
        ("get", "/api/alertas/resumo"),
        ("get", "/api/leituras/1"),
        ("post", "/api/lotes"),
        ("patch", "/api/contas/loja"),
    ]:
        kwargs = {"json": {}} if metodo != "get" else {}
        assert getattr(cliente, metodo)(rota, **kwargs).status_code in (401, 422), rota
    assert (
        cliente.post("/api/lotes", json={"produto_nome": "X", "quantidade": 1, "validade": "2026-12-01"}).status_code
        == 401
    )
