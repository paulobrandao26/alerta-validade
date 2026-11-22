"""Erros de regra de negócio. As rotas os convertem em respostas HTTP."""


class ErroDeNegocio(Exception):
    status_http = 400

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoEncontrado(ErroDeNegocio):
    status_http = 404


class Conflito(ErroDeNegocio):
    status_http = 409


class DadosInvalidos(ErroDeNegocio):
    status_http = 422


class MuitasTentativas(ErroDeNegocio):
    status_http = 429
