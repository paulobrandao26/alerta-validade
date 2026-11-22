"""Conversa com os modelos de IA que leem a embalagem.

Gemini, Groq e Ollama falam o mesmo "idioma" (a API de chat no formato da OpenAI),
então um único cliente atende os três. Eles ficam em fila: se o primeiro falhar
(limite grátis do dia acabou, fora do ar), o próximo tenta.

O resto do sistema só conhece a interface `LeitorDeEmbalagem`.
"""

import base64
import logging
from typing import Protocol

import httpx

from app.modules.leitura_ia.schemas import RespostaIA, RespostaIAInvalida, interpretar_resposta

log = logging.getLogger("validade.ia")


class IAIndisponivel(Exception):
    """Falha passageira (rede, limite da API, servidor fora): vale tentar de novo depois."""


class IANaoConfigurada(Exception):
    """Nenhum provedor configurado: a leitura vai direto para o preenchimento manual."""


class LeitorDeEmbalagem(Protocol):
    def ler(self, imagem: bytes, mime: str) -> RespostaIA: ...


INSTRUCAO = """Você lê fotos de embalagens de produtos de supermercado no Brasil.
Responda SOMENTE com um objeto JSON, sem texto antes ou depois, neste formato:
{"produto": "nome curto do produto ou null", "validade": "AAAA-MM-DD ou null", "confianca": 0.0}

Regras:
- "validade" é a data de VALIDADE/VENCIMENTO (VAL, VENC, "consumir até"). Ignore data de fabricação (FAB) e lote (L).
- Datas no Brasil vêm como DD/MM/AA, DD/MM/AAAA ou MM/AAAA. Se só houver mês e ano, use o último dia do mês.
- "confianca" vai de 0 a 1: o quanto você tem certeza da data.
  Se a data estiver borrada, cortada ou ambígua, use menos de 0.5.
- Se não houver data legível, use "validade": null e "confianca": 0.
- "produto" é o nome como a pessoa chamaria na loja (ex.: "Iogurte natural Nestlé 170g").
  Se não der para saber, null."""

ENDERECOS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "groq": "https://api.groq.com/openai/v1",
}

# Códigos HTTP que indicam problema passageiro ou de conta/limite: o próximo provedor assume.
STATUS_PASSAGEIROS = {401, 402, 403, 404, 408, 409, 429}


class LeitorCompativelOpenAI:
    def __init__(self, nome: str, url_base: str, modelo: str, chave: str = "", timeout: float = 30.0, cliente=None):
        self.nome = nome
        self._url = url_base.rstrip("/") + "/chat/completions"
        self._modelo = modelo
        self._cabecalhos = {"Authorization": f"Bearer {chave}"} if chave else {}
        self._http = cliente or httpx.Client(timeout=timeout)

    def ler(self, imagem: bytes, mime: str) -> RespostaIA:
        foto = f"data:{mime};base64,{base64.standard_b64encode(imagem).decode('ascii')}"
        corpo = {
            "model": self._modelo,
            "temperature": 0,
            "max_tokens": 300,
            "messages": [
                {"role": "system", "content": INSTRUCAO},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Leia o produto e a data de validade desta embalagem."},
                        {"type": "image_url", "image_url": {"url": foto}},
                    ],
                },
            ],
        }
        try:
            resposta = self._http.post(self._url, json=corpo, headers=self._cabecalhos)
        except httpx.HTTPError as erro:  # rede, timeout, DNS
            raise IAIndisponivel(f"{self.nome}: {type(erro).__name__}") from erro
        if resposta.status_code in STATUS_PASSAGEIROS or resposta.status_code >= 500:
            raise IAIndisponivel(f"{self.nome}: HTTP {resposta.status_code}")
        if resposta.status_code >= 400:
            raise RespostaIAInvalida(f"{self.nome}: HTTP {resposta.status_code}")
        try:
            texto = resposta.json()["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as erro:
            raise RespostaIAInvalida(f"{self.nome}: resposta fora do formato") from erro
        return interpretar_resposta(texto)


class LeitorComReserva:
    """Tenta cada provedor na ordem. Para no primeiro que der uma resposta válida."""

    def __init__(self, leitores: list):
        self.leitores = leitores

    def ler(self, imagem: bytes, mime: str) -> RespostaIA:
        houve_indisponivel = False
        for leitor in self.leitores:
            try:
                return leitor.ler(imagem, mime)
            except IAIndisponivel as erro:
                houve_indisponivel = True
                log.warning("Provedor indisponível, tentando o próximo: %s", erro)
            except RespostaIAInvalida as erro:
                log.warning("Resposta inválida, tentando o próximo: %s", erro)
        if houve_indisponivel:
            raise IAIndisponivel("Nenhum provedor de IA respondeu.")
        raise RespostaIAInvalida("Nenhum provedor deu uma resposta válida.")


class LeitorDesligado:
    """Usado quando nenhum provedor está configurado."""

    def ler(self, imagem: bytes, mime: str) -> RespostaIA:
        raise IANaoConfigurada()


def criar_leitor(config) -> LeitorDeEmbalagem:
    leitores = []
    for nome in config.provedores_ativos:
        if nome == "gemini":
            leitores.append(
                LeitorCompativelOpenAI(
                    "gemini",
                    ENDERECOS["gemini"],
                    config.gemini_modelo,
                    config.gemini_api_key,
                    config.ia_timeout_segundos,
                )
            )
        elif nome == "groq":
            leitores.append(
                LeitorCompativelOpenAI(
                    "groq", ENDERECOS["groq"], config.groq_modelo, config.groq_api_key, config.ia_timeout_segundos
                )
            )
        elif nome == "ollama":
            leitores.append(
                LeitorCompativelOpenAI(
                    "ollama",
                    config.ollama_url.rstrip("/") + "/v1",
                    config.ollama_modelo,
                    "",
                    config.ia_timeout_segundos * 4,
                )
            )
    return LeitorComReserva(leitores) if leitores else LeitorDesligado()
