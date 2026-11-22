"""Monta o resumo diário em texto e o link do WhatsApp.

Hoje o envio é por link (a pessoa toca e o WhatsApp abre com a mensagem pronta).
O envio automático precisa da API oficial do WhatsApp Business (ver docs/limitacoes.md).
"""

from urllib.parse import quote

from app.modules.produtos.schemas import LoteSaida

MAXIMO_NA_MENSAGEM = 8


def _linha(lote: LoteSaida) -> str:
    if lote.dias_restantes < 0:
        quando = f"venceu há {-lote.dias_restantes} dia{'s' if lote.dias_restantes < -1 else ''}"
    elif lote.dias_restantes == 0:
        quando = "vence hoje"
    elif lote.dias_restantes == 1:
        quando = "vence amanhã"
    else:
        quando = f"vence em {lote.dias_restantes} dias"
    return f"- {lote.produto_nome} ({lote.quantidade} un.): {quando}"


def montar_mensagem(nome_loja: str, vencidos: list[LoteSaida], atencao: list[LoteSaida], dias_alerta: int) -> str:
    if not vencidos and not atencao:
        return f"{nome_loja}: nenhum produto vencido ou perto de vencer nos próximos {dias_alerta} dias."
    partes = [f"Validades de hoje em {nome_loja}"]
    if vencidos:
        partes.append(f"\nRetirar da prateleira ({len(vencidos)}):")
        partes += [_linha(lote) for lote in vencidos[:MAXIMO_NA_MENSAGEM]]
    if atencao:
        partes.append(f"\nVender primeiro ({len(atencao)}):")
        partes += [_linha(lote) for lote in atencao[:MAXIMO_NA_MENSAGEM]]
    restante = max(0, len(vencidos) - MAXIMO_NA_MENSAGEM) + max(0, len(atencao) - MAXIMO_NA_MENSAGEM)
    if restante:
        partes.append(f"\n+ {restante} outros no painel.")
    return "\n".join(partes)


def link_whatsapp(numero: str, mensagem: str) -> str:
    return f"https://wa.me/55{numero}?text={quote(mensagem)}"
