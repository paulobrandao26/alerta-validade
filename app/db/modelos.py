"""Importa todos os modelos para o SQLAlchemy e o Alembic enxergarem as tabelas."""

from app.db.base import Base
from app.modules.contas.modelos import Loja, Usuario
from app.modules.leitura_ia.modelos import Leitura
from app.modules.produtos.modelos import Lote, Produto

__all__ = ["Base", "Leitura", "Loja", "Lote", "Produto", "Usuario"]
