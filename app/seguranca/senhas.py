"""Senhas guardadas com Argon2 (nunca em texto puro)."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Usado quando o e-mail não existe, para o tempo de resposta ser parecido
# e não denunciar quais e-mails estão cadastrados.
_HASH_FALSO = _hasher.hash("senha-que-ninguem-usa")


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def conferir(senha: str, hash_guardado: str | None) -> bool:
    try:
        return _hasher.verify(hash_guardado or _HASH_FALSO, senha) and hash_guardado is not None
    except (VerificationError, InvalidHashError):
        return False
