"""Datas e horas num lugar só, para os testes conseguirem controlar o "hoje"."""

from datetime import UTC, date, datetime, timedelta, timezone

FUSO_PADRAO = -3


def agora_utc() -> datetime:
    """Data e hora em UTC, sem fuso (é assim que gravamos no banco)."""
    return datetime.now(UTC).replace(tzinfo=None)


def hoje(fuso_horas: int = FUSO_PADRAO) -> date:
    """O dia de hoje no horário da loja."""
    return datetime.now(timezone(timedelta(hours=fuso_horas))).date()
