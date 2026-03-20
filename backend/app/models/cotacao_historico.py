from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class CotacaoHistorico(Base):
    """
    Histórico diário de cotações dos tickers da planilha.
    Salva o valor de fechamento de cada ticker ao final do pregão.
    """
    __tablename__ = "cotacao_historico"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    segmento = Column(String(100), nullable=True)
    valor_fechamento = Column(Float, nullable=True)
    data_referencia = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Garante que não teremos duplicata de ticker + data
    __table_args__ = (
        UniqueConstraint("ticker", "data_referencia", name="uq_ticker_data_referencia"),
    )

    def __repr__(self):
        return (
            f"<CotacaoHistorico(ticker={self.ticker}, "
            f"valor={self.valor_fechamento}, data={self.data_referencia})>"
        )
