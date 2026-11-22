from urllib.parse import unquote


def criar(cliente, nome, validade, quantidade=1):
    assert (
        cliente.post(
            "/api/lotes", json={"produto_nome": nome, "quantidade": quantidade, "validade": validade}
        ).status_code
        == 201
    )


def test_resumo_conta_e_monta_mensagem(logado):
    criar(logado, "Presunto", "2026-11-20", 3)  # vencido há 2 dias
    criar(logado, "Iogurte", "2026-11-22", 10)  # vence hoje
    criar(logado, "Leite", "2026-11-23", 6)  # amanhã
    criar(logado, "Arroz", "2027-06-01", 20)  # tranquilo

    resumo = logado.get("/api/alertas/resumo").json()
    assert (resumo["vencidos"], resumo["atencao"], resumo["ok"]) == (1, 2, 1)
    assert resumo["unidades_em_risco"] == 19
    assert [lote["produto_nome"] for lote in resumo["criticos"]] == ["Presunto", "Iogurte", "Leite"]

    msg = resumo["mensagem"]
    assert "Retirar da prateleira (1)" in msg and "Presunto (3 un.): venceu há 2 dias" in msg
    assert "Iogurte (10 un.): vence hoje" in msg and "Leite (6 un.): vence amanhã" in msg
    assert "Arroz" not in msg
    assert resumo["link_whatsapp"] is None  # a loja ainda não informou o número


def test_link_do_whatsapp_leva_a_mensagem(logado):
    logado.patch("/api/contas/loja", json={"whatsapp": "81 99876-5432"})
    criar(logado, "Queijo", "2026-11-24")
    resumo = logado.get("/api/alertas/resumo").json()
    assert resumo["link_whatsapp"].startswith("https://wa.me/5581998765432?text=")
    assert "Queijo" in unquote(resumo["link_whatsapp"])


def test_sem_nada_critico(logado):
    criar(logado, "Feijão", "2027-08-01")
    resumo = logado.get("/api/alertas/resumo").json()
    assert resumo["criticos"] == [] and "nenhum produto vencido" in resumo["mensagem"]


def test_mensagem_longa_e_resumida(logado):
    for i in range(12):
        criar(logado, f"Produto {i:02d}", "2026-11-23")
    msg = logado.get("/api/alertas/resumo").json()["mensagem"]
    assert "+ 4 outros no painel." in msg
