import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base, ensure_db_schema
from app.core.scheduler import init_scheduler, shutdown_scheduler
from app.api.fundo_imobiliario import router as fii_router
from app.api.cotacao_historico import router as cotacao_router

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Cria as tabelas do banco de dados (inclui cotacao_historico)
# Importa o model para que o Base.metadata conheça a tabela
import app.models.cotacao_historico  # noqa: F401

Base.metadata.create_all(bind=engine)
ensure_db_schema()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia startup e shutdown da aplicação."""
    # Startup
    logger.info("🚀 Iniciando aplicação...")
    init_scheduler()
    yield
    # Shutdown
    logger.info("🛑 Encerrando aplicação...")
    shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para gerenciamento de Fundos Imobiliários (FIIs). "
    "Integração com Google Sheets para obtenção automática de valores e segmentos. "
    "Coleta automática de cotações de fechamento diárias.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS - permite todas as origens (ajustar em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra os routers
app.include_router(fii_router, prefix="/api/v1")
app.include_router(cotacao_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    """Endpoint de saúde da API."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check da aplicação."""
    return {"status": "healthy"}
