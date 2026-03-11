from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.schemas.cotacao_historico import (
    CotacaoHistoricoListResponse,
    SnapshotResultResponse,
)
from app.services.cotacao_historico_service import CotacaoHistoricoService
from app.services.google_sheets_service import get_google_sheets_service, GoogleSheetsService

router = APIRouter(prefix="/cotacoes-historico", tags=["Cotações Histórico"])


def get_service(
    db: Session = Depends(get_db),
    sheets_service: GoogleSheetsService = Depends(get_google_sheets_service),
) -> CotacaoHistoricoService:
    """Dependency injection para o serviço de Cotações Histórico."""
    return CotacaoHistoricoService(db=db, sheets_service=sheets_service)


@router.get(
    "/",
    response_model=CotacaoHistoricoListResponse,
    summary="Listar cotações históricas",
    description="Lista cotações históricas com filtros por ticker, data de início e data de fim.",
)
def listar_historico(
    ticker: Optional[str] = Query(None, description="Filtrar por ticker (busca parcial)"),
    data_inicio: Optional[date] = Query(None, description="Data de início (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data de fim (YYYY-MM-DD)"),
    order_by: Optional[str] = Query(
        "data_referencia",
        description="Ordenar por: ticker, data_referencia, valor_fechamento, segmento",
    ),
    order_direction: Optional[str] = Query("desc", description="Direção: asc ou desc"),
    service: CotacaoHistoricoService = Depends(get_service),
):
    """Retorna cotações históricas com filtros."""
    return service.listar_historico(
        ticker=ticker,
        data_inicio=data_inicio,
        data_fim=data_fim,
        order_by=order_by,
        order_direction=order_direction,
    )


@router.get(
    "/{ticker}",
    response_model=CotacaoHistoricoListResponse,
    summary="Histórico de um ticker",
    description="Retorna todo o histórico de cotações de um ticker específico.",
)
def obter_historico_ticker(
    ticker: str,
    service: CotacaoHistoricoService = Depends(get_service),
):
    """Retorna o histórico completo de cotações de um ticker."""
    return service.obter_historico_por_ticker(ticker)


@router.post(
    "/snapshot",
    response_model=SnapshotResultResponse,
    summary="Executar snapshot manual",
    description="Executa manualmente a coleta de cotações de todos os tickers da planilha para a data informada (ou hoje).",
)
def executar_snapshot(
    data_referencia: Optional[date] = Query(
        None,
        description="Data de referência (YYYY-MM-DD). Se não informada, usa a data de hoje.",
    ),
    service: CotacaoHistoricoService = Depends(get_service),
):
    """
    Executa manualmente o snapshot de cotações.
    Útil para testar ou para salvar valores de uma data específica.
    """
    return service.salvar_snapshot_diario(data_referencia=data_referencia)
