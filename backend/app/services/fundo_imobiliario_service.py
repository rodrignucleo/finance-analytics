import logging
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from fastapi import HTTPException, status

from app.models.fundo_imobiliario import FundoImobiliario
from app.schemas.fundo_imobiliario import (
    FundoImobiliarioCreate,
    FundoImobiliarioUpdate,
)
from app.services.google_sheets_service import GoogleSheetsService

logger = logging.getLogger(__name__)

# Mapeamento de campos permitidos para ordenação
ALLOWED_ORDER_FIELDS = {
    "ticker": FundoImobiliario.ticker,
    "valor_cota": FundoImobiliario.valor_cota,
    "valor_total": FundoImobiliario.valor_total,
    "segmento": FundoImobiliario.segmento,
    "nome": FundoImobiliario.nome,
    "quantidade_cotas": FundoImobiliario.quantidade_cotas,
    "created_at": FundoImobiliario.created_at,
}


class FundoImobiliarioService:
    """Serviço para operações CRUD de Fundos Imobiliários."""

    def __init__(self, db: Session, sheets_service: GoogleSheetsService):
        self.db = db
        self.sheets_service = sheets_service

    def listar_fundos(
        self,
        ticker: str | None = None,
        segmento: str | None = None,
        nome: str | None = None,
        order_by: str = "ticker",
        order_direction: str = "asc",
    ) -> dict:
        """Lista todos os fundos com filtros e ordenação."""
        query = self.db.query(FundoImobiliario)

        # Filtros
        if ticker:
            query = query.filter(FundoImobiliario.ticker.ilike(f"%{ticker}%"))
        if segmento:
            query = query.filter(FundoImobiliario.segmento.ilike(f"%{segmento}%"))
        if nome:
            query = query.filter(FundoImobiliario.nome.ilike(f"%{nome}%"))

        # Ordenação
        order_field = ALLOWED_ORDER_FIELDS.get(order_by, FundoImobiliario.ticker)
        if order_direction.lower() == "desc":
            query = query.order_by(desc(order_field))
        else:
            query = query.order_by(asc(order_field))

        fundos = query.all()

        # Calcula o valor total da carteira
        valor_total_carteira = sum(f.valor_total or 0.0 for f in fundos)

        return {
            "total": len(fundos),
            "items": fundos,
            "valor_total_carteira": round(valor_total_carteira, 2),
        }

    def obter_fundo(self, fundo_id: int) -> FundoImobiliario:
        """Obtém um fundo pelo ID."""
        fundo = self.db.query(FundoImobiliario).filter(FundoImobiliario.id == fundo_id).first()
        if not fundo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fundo com ID {fundo_id} não encontrado.",
            )
        return fundo

    def obter_fundo_por_ticker(self, ticker: str) -> FundoImobiliario | None:
        """Obtém um fundo pelo ticker."""
        return self.db.query(FundoImobiliario).filter(
            FundoImobiliario.ticker == ticker.upper()
        ).first()

    def criar_fundo(self, fundo_data: FundoImobiliarioCreate) -> FundoImobiliario:
        """
        Cria um novo fundo imobiliário.
        1. Verifica se o ticker já existe no banco
        2. Adiciona o ticker na planilha do Google Sheets
        3. Aguarda e obtém os dados (segmento e valor) da planilha
        4. Salva no banco de dados com os dados completos
        """
        ticker = fundo_data.ticker.upper()

        # Verifica se já existe
        existente = self.obter_fundo_por_ticker(ticker)
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Fundo com ticker {ticker} já existe.",
            )

        # 1. Adiciona na planilha do Google Sheets
        try:
            row = self.sheets_service.adicionar_ticker(ticker)
        except Exception as e:
            logger.error(f"Erro ao adicionar ticker na planilha: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erro ao comunicar com Google Sheets: {str(e)}",
            )

        # 2. Obtém os dados da planilha (segmento e valor)
        try:
            dados_planilha = self.sheets_service.obter_dados_ticker(ticker, row)
        except Exception as e:
            logger.error(f"Erro ao obter dados da planilha: {e}")
            dados_planilha = {"segmento": None, "valor_cota": None}

        # 3. Cria o registro no banco de dados
        novo_fundo = FundoImobiliario(
            ticker=ticker,
            nome=fundo_data.nome or ticker,
            segmento=dados_planilha.get("segmento"),
            quantidade_cotas=fundo_data.quantidade_cotas,
            valor_cota=dados_planilha.get("valor_cota"),
        )
        novo_fundo.calcular_valor_total()

        self.db.add(novo_fundo)
        self.db.commit()
        self.db.refresh(novo_fundo)

        logger.info(f"Fundo {ticker} criado com sucesso. ID: {novo_fundo.id}")
        return novo_fundo

    def atualizar_fundo(self, fundo_id: int, fundo_data: FundoImobiliarioUpdate) -> FundoImobiliario:
        """Atualiza um fundo imobiliário existente."""
        fundo = self.obter_fundo(fundo_id)

        # Atualiza somente os campos que foram fornecidos
        update_data = fundo_data.model_dump(exclude_unset=True)

        if "ticker" in update_data:
            update_data["ticker"] = update_data["ticker"].upper()
            # Verifica se o novo ticker já existe
            existente = self.obter_fundo_por_ticker(update_data["ticker"])
            if existente and existente.id != fundo_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Fundo com ticker {update_data['ticker']} já existe.",
                )

        for field, value in update_data.items():
            setattr(fundo, field, value)

        # Recalcula o valor total
        fundo.calcular_valor_total()

        self.db.commit()
        self.db.refresh(fundo)

        logger.info(f"Fundo {fundo.ticker} (ID: {fundo_id}) atualizado com sucesso.")
        return fundo

    def deletar_fundo(self, fundo_id: int) -> dict:
        """
        Deleta um fundo imobiliário.
        Remove também da planilha do Google Sheets.
        """
        fundo = self.obter_fundo(fundo_id)
        ticker = fundo.ticker

        # Remove da planilha
        try:
            self.sheets_service.remover_ticker(ticker)
        except Exception as e:
            logger.warning(f"Erro ao remover ticker da planilha: {e}")

        # Remove do banco de dados
        self.db.delete(fundo)
        self.db.commit()

        logger.info(f"Fundo {ticker} (ID: {fundo_id}) deletado com sucesso.")
        return {"message": f"Fundo {ticker} deletado com sucesso."}

    def atualizar_valores_planilha(self) -> list[FundoImobiliario]:
        """
        Atualiza os valores de todos os fundos a partir da planilha do Google Sheets.
        Útil para sincronizar valores atualizados.
        """
        fundos = self.db.query(FundoImobiliario).all()
        atualizados = []

        for fundo in fundos:
            try:
                dados = self.sheets_service.atualizar_valor_ticker(fundo.ticker)
                if dados and dados.get("valor_cota") is not None:
                    fundo.valor_cota = dados["valor_cota"]
                    if dados.get("segmento"):
                        fundo.segmento = dados["segmento"]
                    fundo.calcular_valor_total()
                    atualizados.append(fundo)
            except Exception as e:
                logger.error(f"Erro ao atualizar valores do fundo {fundo.ticker}: {e}")

        if atualizados:
            self.db.commit()

        logger.info(f"{len(atualizados)} fundos atualizados a partir da planilha.")
        return atualizados
