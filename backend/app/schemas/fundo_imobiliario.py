from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class FundoImobiliarioBase(BaseModel):
    """Schema base para Fundo Imobiliário."""
    ticker: str = Field(..., min_length=4, max_length=10, description="Ticker do fundo (ex: VGHF11)")
    quantidade_cotas: int = Field(..., ge=0, description="Quantidade de cotas do fundo")
    nome: Optional[str] = Field(None, max_length=255, description="Nome do fundo")


class FundoImobiliarioCreate(FundoImobiliarioBase):
    """Schema para criação de Fundo Imobiliário."""
    pass


class FundoImobiliarioUpdate(BaseModel):
    """Schema para atualização de Fundo Imobiliário."""
    ticker: Optional[str] = Field(None, min_length=4, max_length=10)
    nome: Optional[str] = Field(None, max_length=255)
    quantidade_cotas: Optional[int] = Field(None, ge=0)


class FundoImobiliarioResponse(BaseModel):
    """Schema de resposta para Fundo Imobiliário."""
    id: int
    ticker: str
    nome: Optional[str] = None
    segmento: Optional[str] = None
    quantidade_cotas: int
    valor_cota: Optional[float] = None
    valor_total: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FundoImobiliarioListResponse(BaseModel):
    """Schema de resposta para listagem de Fundos Imobiliários."""
    total: int
    items: list[FundoImobiliarioResponse]
    valor_total_carteira: float = 0.0


class FundoImobiliarioFilters(BaseModel):
    """Schema para filtros de busca."""
    ticker: Optional[str] = None
    segmento: Optional[str] = None
    nome: Optional[str] = None
    order_by: Optional[str] = Field("ticker", description="Campo para ordenação: ticker, valor_cota, valor_total, segmento, nome, quantidade_cotas")
    order_direction: Optional[str] = Field("asc", description="Direção da ordenação: asc ou desc")


class MessageResponse(BaseModel):
    """Schema genérico de resposta com mensagem."""
    message: str
    detail: Optional[str] = None
