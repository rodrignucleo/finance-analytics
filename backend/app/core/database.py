from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_db_schema() -> None:
    """
    Migração leve para evoluir o schema sem Alembic.
    Adiciona colunas novas caso não existam.
    """
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE fundos_imobiliarios ADD COLUMN IF NOT EXISTS valor_compra_cota DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE fundos_imobiliarios ADD COLUMN IF NOT EXISTS valor_total_compra DOUBLE PRECISION"))


def get_db():
    """Dependency para injetar sessão do banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
