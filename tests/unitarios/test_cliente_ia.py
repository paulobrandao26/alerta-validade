"""Cliente de IA testado com um servidor falso (nenhuma chamada sai para a internet)."""

import json
from datetime import date

import httpx
import pytest

from app.config import Configuracao
from app.modules.leitura_ia.cliente_ia import (
    IAIndisponivel,
    LeitorCompativelOpenAI,
    LeitorComReserva,
    LeitorDesligado,
    criar_leitor,
)
from app.modules.leitura_ia.schemas import RespostaIA, RespostaIAInvalida

JPEG = b"\xff\xd8\xff\xe0fake"


def resposta_chat(conteudo: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": conteudo}}]}


def leitor_com(responder, chave="chave-secreta"):
    pedidos = []

    def tratar(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return responder(pedido)

    cliente = httpx.Client(transport=httpx.MockTransport(tratar))
    return LeitorCompativelOpenAI("teste", "https://ia.exemplo/v1", "modelo-x", chave, cliente=cliente), pedidos


def test_le_a_resposta_e_monta_o_pedido_certo():
    leitor, pedidos = leitor_com(
        lambda _: httpx.Response(
            200, json=resposta_chat('{"produto": "Leite", "validade": "2026-12-01", "confianca": 0.9}')
        )
    )
    resposta = leitor.ler(JPEG, "image/jpeg")
    assert resposta.validade == date(2026, 12, 1) and resposta.produto == "Leite"

    pedido = pedidos[0]
    assert str(pedido.url) == "https://ia.exemplo/v1/chat/completions"
    assert pedido.headers["authorization"] == "Bearer chave-secreta"
    corpo = json.loads(pedido.content)
    assert corpo["model"] == "modelo-x" and corpo["temperature"] == 0
    imagem = corpo["messages"][1]["content"][1]["image_url"]["url"]
    assert imagem.startswith("data:image/jpeg;base64,")


def test_sem_chave_nao_manda_cabecalho_de_autorizacao():  # caso do Ollama local
    leitor, pedidos = leitor_com(
        lambda _: httpx.Response(200, json=resposta_chat('{"validade": null, "confianca": 0}')), chave=""
    )
    leitor.ler(JPEG, "image/jpeg")
    assert "authorization" not in pedidos[0].headers


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
def test_limite_conta_ou_servidor_fora_e_falha_passageira(status):
    leitor, _ = leitor_com(lambda _: httpx.Response(status, json={"error": "x"}))
    with pytest.raises(IAIndisponivel):
        leitor.ler(JPEG, "image/jpeg")


def test_queda_de_rede_e_falha_passageira():
    def cair(pedido):
        raise httpx.ConnectTimeout("demorou", request=pedido)

    leitor, _ = leitor_com(cair)
    with pytest.raises(IAIndisponivel):
        leitor.ler(JPEG, "image/jpeg")


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(400, json={"error": "imagem inválida"}),
        httpx.Response(200, text="não é json"),
        httpx.Response(200, json={"sem": "choices"}),
        httpx.Response(200, json=resposta_chat("Não consegui ler a data.")),
    ],
)
def test_resposta_fora_do_formato(resposta):
    leitor, _ = leitor_com(lambda _: resposta)
    with pytest.raises(RespostaIAInvalida):
        leitor.ler(JPEG, "image/jpeg")


class Falso:
    def __init__(self, resultado):
        self.resultado = resultado
        self.chamadas = 0

    def ler(self, imagem, mime):
        self.chamadas += 1
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


BOA = RespostaIA(produto="Queijo", validade=date(2026, 12, 3), confianca=0.95)


def test_reserva_assume_quando_o_primeiro_cai():
    gemini, groq = Falso(IAIndisponivel("limite do dia")), Falso(BOA)
    assert LeitorComReserva([gemini, groq]).ler(JPEG, "image/jpeg") == BOA
    assert gemini.chamadas == groq.chamadas == 1


def test_reserva_nao_e_chamada_se_o_primeiro_funciona():
    gemini, groq = Falso(BOA), Falso(BOA)
    LeitorComReserva([gemini, groq]).ler(JPEG, "image/jpeg")
    assert groq.chamadas == 0


def test_reserva_tenta_o_proximo_quando_o_primeiro_responde_lixo():
    assert LeitorComReserva([Falso(RespostaIAInvalida("x")), Falso(BOA)]).ler(JPEG, "image/jpeg") == BOA


def test_todos_fora_do_ar_e_falha_passageira():
    with pytest.raises(IAIndisponivel):
        LeitorComReserva([Falso(IAIndisponivel("a")), Falso(RespostaIAInvalida("b"))]).ler(JPEG, "image/jpeg")


def test_todos_respondendo_lixo_e_resposta_invalida():
    with pytest.raises(RespostaIAInvalida):
        LeitorComReserva([Falso(RespostaIAInvalida("a")), Falso(RespostaIAInvalida("b"))]).ler(JPEG, "image/jpeg")


def test_so_entram_provedores_configurados_e_na_ordem_escolhida():
    config = Configuracao(_env_file=None, ia_provedores="groq, gemini, ollama", gemini_api_key="g", groq_api_key="q")
    assert config.provedores_ativos == ["groq", "gemini"]
    leitor = criar_leitor(config)
    assert [item.nome for item in leitor.leitores] == ["groq", "gemini"]


def test_sem_nenhum_provedor_a_leitura_fica_desligada():
    config = Configuracao(_env_file=None, gemini_api_key="", groq_api_key="", ollama_url="")
    assert config.ia_configurada is False
    assert isinstance(criar_leitor(config), LeitorDesligado)


@pytest.mark.parametrize("status", [401, 429, 500, 400])
def test_mensagem_de_erro_nunca_leva_a_chave(status):
    leitor, _ = leitor_com(lambda _: httpx.Response(status, json={"error": "x"}), chave="sk-SEGREDO-123")
    with pytest.raises((IAIndisponivel, RespostaIAInvalida)) as erro:
        leitor.ler(JPEG, "image/jpeg")
    assert "SEGREDO" not in str(erro.value)
