from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class CotacaoHistoricoResponse(BaseModel):
    """Resposta para uma cotação histórica."""
    id: int
    ticker: str
    segmento: Optional[str] = None
    valor_fechamento: Optional[float] = None
    data_referencia: date
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CotacaoHistoricoListResponse(BaseModel):
    """Resposta para listagem de cotações históricas."""
    total: int
    items: list[CotacaoHistoricoResponse]


class SnapshotResultResponse(BaseModel):
    """Resposta do endpoint de snapshot manual."""
    message: str
    data_referencia: date
    tickers_salvos: int
    tickers_erro: int
    detalhes: list[str] = []
