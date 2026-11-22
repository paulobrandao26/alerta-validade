from datetime import date, datetime
from pathlib import Path

from app.modules.leitura_ia.cliente_ia import IAIndisponivel, IANaoConfigurada
from app.modules.leitura_ia.modelos import Leitura
from app.modules.leitura_ia.schemas import RespostaIA, RespostaIAInvalida
from app.modules.leitura_ia.servico import reivindicar_proxima
from tests.conftest import JPEG


def enviar(cliente, conteudo=JPEG, nome="foto.jpg", tipo="image/jpeg"):
    return cliente.post("/api/leituras", files={"foto": (nome, conteudo, tipo)})


def test_envio_responde_na_hora_e_entra_na_fila(logado, leitor):
    resposta = enviar(logado)
    assert resposta.status_code == 202
    assert resposta.json()["status"] == "pendente"
    assert leitor.chamadas == 0  # a IA não é chamada durante a requisição


def test_fluxo_completo_foto_ia_confirmacao_lote(logado, leitor, rodar_worker):
    leitor.programar(RespostaIA(produto="Iogurte Nestlé 170g", validade=date(2026, 11, 26), confianca=0.93))
    leitura = enviar(logado).json()

    assert rodar_worker() == 1
    lida = logado.get(f"/api/leituras/{leitura['id']}").json()
    assert lida["status"] == "lida"
    assert lida["produto_lido"] == "Iogurte Nestlé 170g" and lida["validade_lida"] == "2026-11-26"

    lote = logado.post(
        f"/api/leituras/{leitura['id']}/confirmar",
        json={"produto_nome": "Iogurte Nestlé 170g", "validade": "2026-11-26", "quantidade": 12},
    )
    assert lote.status_code == 201
    assert lote.json()["origem"] == "foto" and lote.json()["estado"] == "atencao"
    assert logado.get(f"/api/leituras/{leitura['id']}").json()["status"] == "confirmada"

    # Confirmar de novo não cria um segundo lote.
    repetida = logado.post(
        f"/api/leituras/{leitura['id']}/confirmar",
        json={"produto_nome": "Iogurte Nestlé 170g", "validade": "2026-11-26", "quantidade": 12},
    )
    assert repetida.status_code == 409
    assert len(logado.get("/api/lotes").json()) == 1


def test_pouca_confianca_vai_para_revisao(logado, leitor, rodar_worker):
    leitor.programar(RespostaIA(produto="Queijo", validade=date(2026, 12, 1), confianca=0.4))
    leitura = enviar(logado).json()
    rodar_worker()
    estado = logado.get(f"/api/leituras/{leitura['id']}").json()
    assert estado["status"] == "revisao"
    assert estado["validade_lida"] == "2026-12-01"  # a sugestão fica para a pessoa conferir


def test_data_absurda_vai_para_revisao_mesmo_com_confianca_alta(logado, leitor, rodar_worker):
    leitor.programar(RespostaIA(produto="Biscoito", validade=date(2019, 3, 1), confianca=0.99))
    leitura = enviar(logado).json()
    rodar_worker()
    assert logado.get(f"/api/leituras/{leitura['id']}").json()["status"] == "revisao"


def test_resposta_invalida_da_ia_vai_para_revisao(logado, leitor, rodar_worker):
    leitor.programar(RespostaIAInvalida("lixo"))
    leitura = enviar(logado).json()
    rodar_worker()
    assert logado.get(f"/api/leituras/{leitura['id']}").json()["status"] == "revisao"


def test_ia_fora_do_ar_volta_para_fila_e_depois_vai_para_revisao(app, logado, leitor, config, rodar_worker):
    leitor.programar(IAIndisponivel("timeout"), IAIndisponivel("timeout"), IAIndisponivel("timeout"))
    leitura_id = enviar(logado).json()["id"]

    for tentativa in range(1, config.leitura_max_tentativas + 1):
        with app.state.fabrica_sessao() as sessao:  # simula o tempo de espera passando
            sessao.get(Leitura, leitura_id).proxima_tentativa_em = datetime(2000, 1, 1)
            sessao.commit()
        rodar_worker()
        estado = logado.get(f"/api/leituras/{leitura_id}").json()
        if tentativa < config.leitura_max_tentativas:
            assert estado["status"] == "pendente", "a foto não pode se perder"
    assert estado["status"] == "revisao"
    assert leitor.chamadas == config.leitura_max_tentativas


def test_ia_fora_do_ar_espera_antes_de_tentar_de_novo(logado, leitor, rodar_worker):
    leitor.programar(IAIndisponivel("timeout"))
    enviar(logado)
    rodar_worker()
    assert rodar_worker() == 0  # ainda no tempo de espera
    assert leitor.chamadas == 1


def test_sem_ia_configurada_vai_direto_para_preenchimento(logado, leitor, rodar_worker):
    leitor.programar(IANaoConfigurada())
    leitura = enviar(logado).json()
    rodar_worker()
    estado = logado.get(f"/api/leituras/{leitura['id']}").json()
    assert estado["status"] == "revisao" and "desligada" in estado["erro"]


def test_dois_workers_nao_pegam_a_mesma_foto(app, logado):
    enviar(logado)
    with app.state.fabrica_sessao() as s1, app.state.fabrica_sessao() as s2:
        primeiro = reivindicar_proxima(s1)
        segundo = reivindicar_proxima(s2)
    assert primeiro is not None and segundo is None


def test_recusa_arquivo_que_nao_e_foto(logado):
    assert enviar(logado, b"<html><script>alert(1)</script>", "foto.jpg", "image/jpeg").status_code == 422
    assert enviar(logado, b"MZ\x90\x00" * 10, "virus.exe", "image/png").status_code == 422


def test_recusa_foto_grande_demais(logado, config):
    assert enviar(logado, JPEG + b"\x00" * config.upload_max_bytes).status_code == 422


def test_limite_de_fotos_por_minuto(logado, config):
    for _ in range(config.fotos_por_minuto):
        assert enviar(logado).status_code == 202
    assert enviar(logado).status_code == 429


def fotos_guardadas(config):
    pasta = Path(config.pasta_uploads)
    return list(pasta.iterdir()) if pasta.exists() else []


def test_foto_e_apagada_depois_da_leitura(logado, leitor, config, rodar_worker):
    leitor.programar(RespostaIA(produto="Leite", validade=date(2026, 12, 1), confianca=0.9))
    enviar(logado)
    assert len(fotos_guardadas(config)) == 1  # na fila, a foto precisa existir
    rodar_worker()
    assert fotos_guardadas(config) == []  # lida: sem custo de armazenamento


def test_foto_fica_enquanto_a_ia_vai_tentar_de_novo(logado, leitor, config, rodar_worker):
    leitor.programar(IAIndisponivel("timeout"))
    enviar(logado)
    rodar_worker()
    assert len(fotos_guardadas(config)) == 1  # ainda vai precisar dela na próxima tentativa


def test_foto_e_apagada_mesmo_quando_vai_para_revisao(logado, leitor, config, rodar_worker):
    leitor.programar(RespostaIAInvalida("lixo"))
    enviar(logado)
    rodar_worker()
    assert fotos_guardadas(config) == []


def test_nao_existe_rota_para_baixar_fotos(logado):
    leitura = enviar(logado).json()
    assert logado.get(f"/api/leituras/{leitura['id']}/foto").status_code == 404
