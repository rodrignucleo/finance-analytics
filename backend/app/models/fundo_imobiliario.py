from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class SegmentoFII(str, enum.Enum):
    """Segmentos de Fundos Imobiliários."""
    PAPEL = "Papel"
    TIJOLO = "Tijolo"
    HIBRIDO = "Híbrido"
    FUNDO_DE_FUNDOS = "Fundo de Fundos"
    DESENVOLVIMENTO = "Desenvolvimento"
    HOTEL = "Hotel"
    HOSPITAL = "Hospital"
    LAJES_CORPORATIVAS = "Lajes Corporativas"
    LOGISTICA = "Logística"
    RENDA_URBANA = "Renda Urbana"
    SHOPPINGS = "Shoppings"
    AGRO = "Agro"
    EDUCACIONAL = "Educacional"
    PAPEL_MISTO = "Papel / Misto (Hedge Fund)"
    OUTROS = "Outros"


class FundoImobiliario(Base):
    __tablename__ = "fundos_imobiliarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    nome = Column(String(255), nullable=True)
    segmento = Column(String(100), nullable=True)
    quantidade_cotas = Column(Integer, nullable=False, default=0)
    valor_cota = Column(Float, nullable=True)
    valor_total = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FundoImobiliario(ticker={self.ticker}, cotas={self.quantidade_cotas}, valor_cota={self.valor_cota})>"

    def calcular_valor_total(self):
        """Calcula o valor total baseado na quantidade de cotas e valor da cota."""
        if self.valor_cota and self.quantidade_cotas:
            self.valor_total = round(self.valor_cota * self.quantidade_cotas, 2)
        else:
            self.valor_total = 0.0
