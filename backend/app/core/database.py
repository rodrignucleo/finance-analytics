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

        # Garante que a tabela cotacao_historico existe (criada pelo create_all, mas verifica constraint)
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'uq_ticker_data_referencia'
                ) THEN
                    ALTER TABLE cotacao_historico
                    ADD CONSTRAINT uq_ticker_data_referencia UNIQUE (ticker, data_referencia);
                END IF;
            EXCEPTION WHEN undefined_table THEN
                NULL;
            END $$;
        """))


def get_db():
    """Dependency para injetar sessão do banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
