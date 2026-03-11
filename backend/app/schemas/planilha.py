from pydantic import BaseModel, Field
from typing import Optional


class PlanilhaTickerCreate(BaseModel):
    ticker: str = Field(..., min_length=4, max_length=10, description="Ticker do fundo (ex: VGHF11)")


class PlanilhaTickerData(BaseModel):
    ticker: str
    segmento: Optional[str] = None
    valor_cota: Optional[float] = None


class PlanilhaTickerAddResponse(BaseModel):
    ticker: str
    row: int
    created: bool


class PlanilhaTickersResponse(BaseModel):
    total: int
    items: list[PlanilhaTickerData]


class CalcularCarteiraCreate(BaseModel):
    ticker: str = Field(..., min_length=4, max_length=10)
    quantidade_cotas: int = Field(..., ge=0)
    valor_compra_cota: float = Field(..., ge=0, description="Preço de compra por cota")
    nome: Optional[str] = Field(None, max_length=255)


