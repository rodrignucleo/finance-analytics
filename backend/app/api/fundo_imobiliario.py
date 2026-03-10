from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.fundo_imobiliario import (
    FundoImobiliarioCreate,
    FundoImobiliarioUpdate,
    FundoImobiliarioResponse,
    FundoImobiliarioListResponse,
    MessageResponse,
)
from app.services.fundo_imobiliario_service import FundoImobiliarioService
from app.services.google_sheets_service import get_google_sheets_service, GoogleSheetsService

router = APIRouter(prefix="/fundos-imobiliarios", tags=["Fundos Imobiliários"])


def get_service(
    db: Session = Depends(get_db),
    sheets_service: GoogleSheetsService = Depends(get_google_sheets_service),
) -> FundoImobiliarioService:
    """Dependency injection para o serviço de Fundos Imobiliários."""
    return FundoImobiliarioService(db=db, sheets_service=sheets_service)


@router.get(
    "/",
    response_model=FundoImobiliarioListResponse,
    summary="Listar Fundos Imobiliários",
    description="Lista todos os fundos imobiliários com filtros e ordenação.",
)
def listar_fundos(
    ticker: Optional[str] = Query(None, description="Filtrar por ticker (busca parcial)"),
    segmento: Optional[str] = Query(None, description="Filtrar por segmento (busca parcial)"),
    nome: Optional[str] = Query(None, description="Filtrar por nome (busca parcial)"),
    order_by: Optional[str] = Query(
        "ticker",
        description="Ordenar por: ticker, valor_cota, valor_total, segmento, nome, quantidade_cotas",
    ),
    order_direction: Optional[str] = Query("asc", description="Direção: asc ou desc"),
    service: FundoImobiliarioService = Depends(get_service),
):
    """Retorna a lista de fundos imobiliários com suporte a filtros e ordenação."""
    return service.listar_fundos(
        ticker=ticker,
        segmento=segmento,
        nome=nome,
        order_by=order_by,
        order_direction=order_direction,
    )


@router.get(
    "/{fundo_id}",
    response_model=FundoImobiliarioResponse,
    summary="Obter Fundo por ID",
    description="Retorna os detalhes de um fundo imobiliário específico.",
)
def obter_fundo(
    fundo_id: int,
    service: FundoImobiliarioService = Depends(get_service),
):
    """Retorna os detalhes de um fundo imobiliário pelo ID."""
    return service.obter_fundo(fundo_id)


@router.post(
    "/",
    response_model=FundoImobiliarioResponse,
    status_code=201,
    summary="Adicionar Fundo Imobiliário",
    description="Adiciona um novo fundo imobiliário. O ticker é adicionado na planilha do Google Sheets para obter segmento e valor automaticamente.",
)
def criar_fundo(
    fundo: FundoImobiliarioCreate,
    service: FundoImobiliarioService = Depends(get_service),
):
    """
    Cria um novo fundo imobiliário:
    1. Adiciona o ticker na planilha do Google Sheets
    2. Aguarda a planilha preencher segmento e valor via Google Finance
    3. Salva no banco de dados PostgreSQL com os dados completos
    """
    return service.criar_fundo(fundo)


@router.put(
    "/{fundo_id}",
    response_model=FundoImobiliarioResponse,
    summary="Atualizar Fundo Imobiliário",
    description="Atualiza os dados de um fundo imobiliário existente.",
)
def atualizar_fundo(
    fundo_id: int,
    fundo: FundoImobiliarioUpdate,
    service: FundoImobiliarioService = Depends(get_service),
):
    """Atualiza um fundo imobiliário existente."""
    return service.atualizar_fundo(fundo_id, fundo)


@router.delete(
    "/{fundo_id}",
    response_model=MessageResponse,
    summary="Deletar Fundo Imobiliário",
    description="Remove um fundo imobiliário do banco de dados e da planilha.",
)
def deletar_fundo(
    fundo_id: int,
    service: FundoImobiliarioService = Depends(get_service),
):
    """Deleta um fundo imobiliário do banco e da planilha do Google Sheets."""
    return service.deletar_fundo(fundo_id)


@router.post(
    "/sync-valores",
    response_model=MessageResponse,
    summary="Sincronizar valores da planilha",
    description="Atualiza os valores de todos os fundos a partir da planilha do Google Sheets.",
)
def sincronizar_valores(
    service: FundoImobiliarioService = Depends(get_service),
):
    """Sincroniza os valores de todos os fundos a partir da planilha do Google Sheets."""
    atualizados = service.atualizar_valores_planilha()
    return {
        "message": f"{len(atualizados)} fundos atualizados com sucesso.",
        "detail": f"Fundos atualizados: {', '.join(f.ticker for f in atualizados)}" if atualizados else "Nenhum fundo atualizado.",
    }
