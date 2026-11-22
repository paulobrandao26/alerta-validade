"""Middlewares de proteção: cabeçalhos de segurança e bloqueio de CSRF."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

CABECALHO_CSRF = "X-Requested-With"
VALOR_CSRF = "validade-certa"
METODOS_QUE_ALTERAM = {"POST", "PUT", "PATCH", "DELETE"}

POLITICA_CONTEUDO = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' blob: data:",
        "connect-src 'self'",
        "manifest-src 'self'",
        "worker-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


class CabecalhosDeSeguranca(BaseHTTPMiddleware):
    def __init__(self, app, producao: bool = False):
        super().__init__(app)
        self.producao = producao

    async def dispatch(self, request: Request, call_next):
        resposta = await call_next(request)
        h = resposta.headers
        h.setdefault("Content-Security-Policy", POLITICA_CONTEUDO)
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if request.url.path.startswith("/api/"):
            h.setdefault("Cache-Control", "no-store")
        if self.producao:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resposta


class BloqueioCSRF(BaseHTTPMiddleware):
    """Toda requisição que altera dados precisa de um cabeçalho que só o nosso app envia.

    Um site malicioso não consegue mandar esse cabeçalho para cá sem permissão de CORS
    (que não damos). Junto com o cookie SameSite=Strict, isso fecha a porta do CSRF.
    """

    async def dispatch(self, request: Request, call_next):
        if (
            request.method in METODOS_QUE_ALTERAM
            and request.url.path.startswith("/api/")
            and request.headers.get(CABECALHO_CSRF) != VALOR_CSRF
        ):
            return JSONResponse({"detail": "Requisição recusada."}, status_code=403)
        return await call_next(request)
