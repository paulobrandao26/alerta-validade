from datetime import date

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.modules.alertas.notificador import link_whatsapp, montar_mensagem
from app.modules.alertas.regras import Estado
from app.modules.contas.modelos import Loja
from app.modules.produtos import repositorio
from app.modules.produtos.schemas import LoteSaida
from app.modules.produtos.servico import para_saida


class Resumo(BaseModel):
    vencidos: int
    atencao: int
    ok: int
    unidades_em_risco: int
    criticos: list[LoteSaida]
    mensagem: str
    link_whatsapp: str | None


def resumir(sessao: Session, loja: Loja, hoje: date) -> Resumo:
    lotes = [para_saida(lote, hoje, loja.dias_alerta) for lote in repositorio.listar_lotes_ativos(sessao, loja.id)]
    vencidos = [lote for lote in lotes if lote.estado == Estado.VENCIDO]
    atencao = [lote for lote in lotes if lote.estado == Estado.ATENCAO]
    criticos = vencidos + atencao
    mensagem = montar_mensagem(loja.nome, vencidos, atencao, loja.dias_alerta)
    return Resumo(
        vencidos=len(vencidos),
        atencao=len(atencao),
        ok=len(lotes) - len(criticos),
        unidades_em_risco=sum(lote.quantidade for lote in criticos),
        criticos=criticos,
        mensagem=mensagem,
        link_whatsapp=link_whatsapp(loja.whatsapp, mensagem) if loja.whatsapp else None,
    )
