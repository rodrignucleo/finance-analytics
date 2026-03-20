import logging
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc

from app.models.cotacao_historico import CotacaoHistorico
from app.services.google_sheets_service import GoogleSheetsService

logger = logging.getLogger(__name__)


class CotacaoHistoricoService:
    """Serviço para gerenciar cotações históricas."""

    def __init__(self, db: Session, sheets_service: GoogleSheetsService):
        self.db = db
        self.sheets_service = sheets_service

    def salvar_snapshot_diario(self, data_referencia: date | None = None) -> dict:
        """
        Lê todos os tickers da planilha do Google Sheets e salva o valor
        de fechamento no banco de dados para a data de referência.

        Se a cotação para o ticker+data já existir, atualiza o valor.
        """
        if data_referencia is None:
            data_referencia = date.today()

        logger.info(f"Iniciando snapshot de cotações para {data_referencia}")

        # 1. Obtém todos os tickers e valores da planilha
        try:
            dados_planilha = self.sheets_service.obter_todos_dados()
        except Exception as e:
            logger.error(f"Erro ao obter dados da planilha: {e}")
            return {
                "message": f"Erro ao acessar a planilha: {str(e)}",
                "data_referencia": data_referencia,
                "tickers_salvos": 0,
                "tickers_erro": 0,
                "detalhes": [str(e)],
            }

        tickers_salvos = 0
        tickers_erro = 0
        detalhes = []

        for dados in dados_planilha:
            ticker = dados.get("ticker", "").strip().upper()
            if not ticker:
                continue

            valor_cota = dados.get("valor_cota")
            segmento = dados.get("segmento")

            try:
                # Verifica se já existe registro para esse ticker+data
                existente = (
                    self.db.query(CotacaoHistorico)
                    .filter(
                        CotacaoHistorico.ticker == ticker,
                        CotacaoHistorico.data_referencia == data_referencia,
                    )
                    .first()
                )

                if existente:
                    # Atualiza o valor existente
                    existente.valor_fechamento = valor_cota
                    existente.segmento = segmento
                    detalhes.append(f"{ticker}: atualizado → R$ {valor_cota}")
                else:
                    # Cria novo registro
                    nova_cotacao = CotacaoHistorico(
                        ticker=ticker,
                        segmento=segmento,
                        valor_fechamento=valor_cota,
                        data_referencia=data_referencia,
                    )
                    self.db.add(nova_cotacao)
                    detalhes.append(f"{ticker}: salvo → R$ {valor_cota}")

                tickers_salvos += 1

            except Exception as e:
                logger.error(f"Erro ao salvar cotação de {ticker}: {e}")
                tickers_erro += 1
                detalhes.append(f"{ticker}: ERRO → {str(e)}")

        # Commit de tudo de uma vez
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao commitar cotações: {e}")
            self.db.rollback()
            return {
                "message": f"Erro ao salvar no banco: {str(e)}",
                "data_referencia": data_referencia,
                "tickers_salvos": 0,
                "tickers_erro": len(dados_planilha),
                "detalhes": [str(e)],
            }

        msg = f"Snapshot concluído para {data_referencia}: {tickers_salvos} salvos, {tickers_erro} erros."
        logger.info(msg)

        return {
            "message": msg,
            "data_referencia": data_referencia,
            "tickers_salvos": tickers_salvos,
            "tickers_erro": tickers_erro,
            "detalhes": detalhes,
        }

    def listar_historico(
        self,
        ticker: str | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        order_by: str = "data_referencia",
        order_direction: str = "desc",
    ) -> dict:
        """Lista cotações históricas com filtros."""
        query = self.db.query(CotacaoHistorico)

        if ticker:
            query = query.filter(CotacaoHistorico.ticker.ilike(f"%{ticker}%"))
        if data_inicio:
            query = query.filter(CotacaoHistorico.data_referencia >= data_inicio)
        if data_fim:
            query = query.filter(CotacaoHistorico.data_referencia <= data_fim)

        # Ordenação
        order_fields = {
            "ticker": CotacaoHistorico.ticker,
            "data_referencia": CotacaoHistorico.data_referencia,
            "valor_fechamento": CotacaoHistorico.valor_fechamento,
            "segmento": CotacaoHistorico.segmento,
        }
        order_field = order_fields.get(order_by, CotacaoHistorico.data_referencia)

        if order_direction.lower() == "asc":
            query = query.order_by(asc(order_field))
        else:
            query = query.order_by(desc(order_field))

        cotacoes = query.all()

        return {
            "total": len(cotacoes),
            "items": cotacoes,
        }

    def obter_historico_por_ticker(self, ticker: str) -> dict:
        """Obtém todo o histórico de um ticker específico, ordenado por data."""
        cotacoes = (
            self.db.query(CotacaoHistorico)
            .filter(CotacaoHistorico.ticker == ticker.upper())
            .order_by(desc(CotacaoHistorico.data_referencia))
            .all()
        )

        return {
            "total": len(cotacoes),
            "items": cotacoes,
        }
