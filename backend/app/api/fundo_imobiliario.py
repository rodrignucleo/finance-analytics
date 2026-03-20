from fastapi import APIRouter, Depends, Query, Response
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
from app.schemas.planilha import (
    PlanilhaTickerCreate,
    PlanilhaTickerAddResponse,
    PlanilhaTickersResponse,
    PlanilhaTickerData,
    CalcularCarteiraCreate,
)

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
    "/planilha",
    response_model=PlanilhaTickersResponse,
    summary="Listar tickers da planilha",
    description="Lista todos os tickers existentes na planilha (com segmento e valor, se disponíveis).",
)
def listar_tickers_planilha(
    sheets_service: GoogleSheetsService = Depends(get_google_sheets_service),
):
    from fastapi import HTTPException, status

    try:
        items = [PlanilhaTickerData(**x) for x in sheets_service.obter_todos_dados()]
        return {"total": len(items), "items": items}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erro ao acessar Google Sheets: {str(e)}")


@router.get(
    "/planilha/{ticker}",
    response_model=PlanilhaTickerData,
    summary="Buscar ticker na planilha",
    description="Busca um ticker na planilha e retorna segmento e valor.",
)
def obter_ticker_planilha(
    ticker: str,
    sheets_service: GoogleSheetsService = Depends(get_google_sheets_service),
):
    from fastapi import HTTPException, status

    try:
        dados = sheets_service.obter_dados_por_ticker(ticker, max_retries=2, delay=1.0)
        return PlanilhaTickerData(**dados)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erro ao acessar Google Sheets: {str(e)}")


@router.post(
    "/planilha",
    response_model=PlanilhaTickerAddResponse,
    status_code=201,
    summary="Adicionar ticker na planilha",
    description="Adiciona o ticker na primeira linha vazia da coluna A. Se já existir, retorna 409.",
)
def adicionar_ticker_planilha(
    payload: PlanilhaTickerCreate,
    sheets_service: GoogleSheetsService = Depends(get_google_sheets_service),
):
    from fastapi import HTTPException, status

    try:
        row, created = sheets_service.adicionar_ticker_primeira_linha_vazia(payload.ticker)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erro ao acessar Google Sheets: {str(e)}")
    if not created:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticker {payload.ticker.strip().upper()} já existe na planilha (linha {row}).",
        )
    return {"ticker": payload.ticker.strip().upper(), "row": row, "created": True}


@router.post(
    "/calcular",
    response_model=FundoImobiliarioResponse,
    summary="Calcular e salvar posição por ticker",
    description="Lê segmento e valor da planilha, calcula valor_total pela quantidade de cotas e salva no banco. Se o ticker já existir no banco, retorna 409.",
)
def calcular_e_salvar(
    payload: CalcularCarteiraCreate,
    response: Response,
    service: FundoImobiliarioService = Depends(get_service),
):
    fundo, created = service.salvar_posicao_calculada(
        ticker=payload.ticker,
        quantidade_cotas=payload.quantidade_cotas,
        valor_compra_cota=payload.valor_compra_cota,
        nome=payload.nome,
    )
    response.status_code = 201 if created else 200
    return fundo


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
