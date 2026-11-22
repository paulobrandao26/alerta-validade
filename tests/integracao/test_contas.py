from tests.conftest import SENHA, cadastrar


def test_cadastro_abre_sessao_com_cookie_protegido(novo_cliente):
    cliente = novo_cliente()
    conta = cadastrar(cliente, email="Dono@Mercado.com ")
    assert conta["usuario"]["email"] == "dono@mercado.com"
    assert conta["loja"]["dias_alerta"] == 7
    assert conta["ia_ligada"] is False

    cookie = next(c for c in cliente.cookies.jar if c.name == "vc_sessao")
    assert cookie.has_nonstandard_attr("HttpOnly")
    assert cliente.get("/api/contas/eu").status_code == 200


def test_resposta_nunca_devolve_a_senha(novo_cliente):
    cliente = novo_cliente()
    texto = cliente.post("/api/contas/cadastro", json={"nome_loja": "Loja", "email": "a@b.com", "senha": SENHA}).text
    assert SENHA not in texto and "senha_hash" not in texto and "argon2" not in texto


def test_email_repetido_da_conflito(novo_cliente):
    cadastrar(novo_cliente())
    resposta = novo_cliente().post(
        "/api/contas/cadastro", json={"nome_loja": "Outra", "email": "dono@mercado.com", "senha": SENHA}
    )
    assert resposta.status_code == 409


def test_senha_curta_e_email_invalido_sao_recusados(novo_cliente):
    cliente = novo_cliente()
    assert (
        cliente.post("/api/contas/cadastro", json={"nome_loja": "Loja", "email": "a@b.com", "senha": "123"}).status_code
        == 422
    )
    assert (
        cliente.post(
            "/api/contas/cadastro", json={"nome_loja": "Loja", "email": "nao-e-email", "senha": SENHA}
        ).status_code
        == 422
    )


def test_entrar_e_sair(novo_cliente):
    cadastrar(novo_cliente())
    cliente = novo_cliente()
    assert cliente.get("/api/contas/eu").status_code == 401
    assert cliente.post("/api/contas/entrar", json={"email": "dono@mercado.com", "senha": SENHA}).status_code == 200
    assert cliente.get("/api/contas/eu").status_code == 200
    assert cliente.post("/api/contas/sair").status_code == 204
    assert cliente.get("/api/contas/eu").status_code == 401


def test_senha_errada_e_email_inexistente_tem_a_mesma_resposta(novo_cliente):
    cadastrar(novo_cliente())
    cliente = novo_cliente()
    errada = cliente.post("/api/contas/entrar", json={"email": "dono@mercado.com", "senha": "errada-123"})
    inexistente = cliente.post("/api/contas/entrar", json={"email": "ninguem@mercado.com", "senha": "errada-123"})
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json()


def test_bloqueia_depois_de_muitas_tentativas(novo_cliente, config):
    cadastrar(novo_cliente())
    cliente = novo_cliente()
    for _ in range(config.login_max_tentativas):
        assert (
            cliente.post("/api/contas/entrar", json={"email": "dono@mercado.com", "senha": "errada-123"}).status_code
            == 401
        )
    # Nem a senha certa entra enquanto o bloqueio durar.
    assert cliente.post("/api/contas/entrar", json={"email": "dono@mercado.com", "senha": SENHA}).status_code == 429


def test_cookie_adulterado_nao_entra(novo_cliente):
    cliente = novo_cliente()
    cliente.cookies.set("vc_sessao", "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0.")  # token "sem assinatura"
    assert cliente.get("/api/contas/eu").status_code == 401


def test_ajustes_da_loja(logado):
    resposta = logado.patch("/api/contas/loja", json={"dias_alerta": 10, "whatsapp": "(81) 99876-5432"})
    assert resposta.status_code == 200
    assert resposta.json()["whatsapp"] == "81998765432"
    assert logado.patch("/api/contas/loja", json={"whatsapp": "123"}).status_code == 422
    assert logado.patch("/api/contas/loja", json={"dias_alerta": 0}).status_code == 422
    assert logado.patch("/api/contas/loja", json={"whatsapp": ""}).json()["whatsapp"] is None
