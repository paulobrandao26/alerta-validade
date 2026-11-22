from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.sessao import obter_sessao
from app.modules.contas.modelos import Usuario
from app.modules.leitura_ia import arquivos, servico
from app.modules.leitura_ia.schemas import Confirmacao, LeituraSaida
from app.modules.produtos.schemas import LoteSaida
from app.modules.produtos.servico import para_saida
from app.nucleo import relogio
from app.seguranca.dependencias import usuario_atual

rotas = APIRouter(prefix="/api/leituras", tags=["leitura por foto"])


@rotas.post("", response_model=LeituraSaida, status_code=status.HTTP_202_ACCEPTED)
async def enviar_foto(
    request: Request,
    foto: UploadFile = File(...),
    usuario: Usuario = Depends(usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Recebe a foto e responde na hora. A IA lê depois, no worker."""
    config = request.app.state.config
    if not request.app.state.limitador_fotos.tentar(f"u{usuario.id}"):
        raise HTTPException(status_code=429, detail="Muitas fotos em pouco tempo. Espere um minuto.")
    conteudo = await foto.read(config.upload_max_bytes + 1)
    mime = arquivos.validar_foto(conteudo, config.upload_max_bytes)
    nome = arquivos.salvar_foto(config.pasta_uploads, conteudo, mime)
    return servico.registrar(sessao, usuario.loja_id, usuario.id, nome, mime)


@rotas.get("/{leitura_id}", response_model=LeituraSaida)
def consultar(leitura_id: int, usuario: Usuario = Depends(usuario_atual), sessao: Session = Depends(obter_sessao)):
    return servico.buscar(sessao, usuario.loja_id, leitura_id)


@rotas.post("/{leitura_id}/confirmar", response_model=LoteSaida, status_code=status.HTTP_201_CREATED)
def confirmar(
    leitura_id: int,
    dados: Confirmacao,
    request: Request,
    usuario: Usuario = Depends(usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    hoje = relogio.hoje(request.app.state.config.fuso_horas)
    lote = servico.confirmar(sessao, usuario.loja_id, leitura_id, dados, hoje)
    return para_saida(lote, hoje, usuario.loja.dias_alerta)
