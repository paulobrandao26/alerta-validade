from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.contas import repositorio
from app.modules.contas.modelos import Loja, Usuario
from app.modules.contas.schemas import AjustesLoja, Cadastro
from app.nucleo.erros import Conflito, MuitasTentativas
from app.seguranca import senhas
from app.seguranca.limitador import Limitador


def cadastrar(sessao: Session, dados: Cadastro) -> Usuario:
    if repositorio.buscar_por_email(sessao, dados.email):
        raise Conflito('Este e-mail já tem conta. Use "Entrar".')
    try:
        usuario = repositorio.criar_loja_com_dono(sessao, dados.nome_loja, dados.email, senhas.gerar_hash(dados.senha))
        sessao.commit()
    except IntegrityError as erro:  # dois cadastros iguais ao mesmo tempo
        sessao.rollback()
        raise Conflito('Este e-mail já tem conta. Use "Entrar".') from erro
    return usuario


def autenticar(sessao: Session, email: str, senha: str, ip: str, limitador: Limitador) -> Usuario | None:
    """Confere e-mail e senha, com limite de tentativas por IP + e-mail."""
    chave = f"{ip}|{email}"
    if limitador.bloqueado(chave):
        raise MuitasTentativas("Muitas tentativas. Espere alguns minutos e tente de novo.")
    usuario = repositorio.buscar_por_email(sessao, email)
    if not senhas.conferir(senha, usuario.senha_hash if usuario else None):
        limitador.registrar(chave)
        return None
    limitador.zerar(chave)
    return usuario


def ajustar_loja(sessao: Session, loja: Loja, dados: AjustesLoja) -> Loja:
    if dados.nome is not None:
        loja.nome = " ".join(dados.nome.split())
    if dados.dias_alerta is not None:
        loja.dias_alerta = dados.dias_alerta
    if dados.whatsapp is not None:
        loja.whatsapp = dados.whatsapp or None
    sessao.commit()
    return loja
