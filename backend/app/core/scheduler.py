"""
Scheduler para jobs periódicos.

O mercado de FIIs na B3 fecha às 17:30 (horário de Brasília).
O job roda às 18:00 (BRT / America/Sao_Paulo) de segunda a sexta
para garantir que os valores já foram atualizados.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import SessionLocal
from app.services.google_sheets_service import GoogleSheetsService
from app.services.cotacao_historico_service import CotacaoHistoricoService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def job_snapshot_fechamento():
    """
    Job que salva o snapshot de cotações no fechamento do mercado.
    Executa de segunda a sexta às 18:00 (America/Sao_Paulo).
    """
    logger.info("🕕 [Scheduler] Iniciando snapshot de fechamento diário...")

    db = SessionLocal()
    try:
        sheets_service = GoogleSheetsService()
        cotacao_service = CotacaoHistoricoService(db=db, sheets_service=sheets_service)

        resultado = cotacao_service.salvar_snapshot_diario()

        logger.info(
            f"✅ [Scheduler] Snapshot concluído: "
            f"{resultado['tickers_salvos']} salvos, "
            f"{resultado['tickers_erro']} erros."
        )

        for detalhe in resultado.get("detalhes", []):
            logger.info(f"   → {detalhe}")

    except Exception as e:
        logger.error(f"❌ [Scheduler] Erro no snapshot de fechamento: {e}", exc_info=True)
    finally:
        db.close()


def init_scheduler():
    """Inicializa o scheduler com os jobs configurados."""

    # Job de snapshot no fechamento do mercado
    # Roda de segunda (0) a sexta (4) às 18:00 horário de São Paulo
    scheduler.add_job(
        job_snapshot_fechamento,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=18,
            minute=0,
            timezone="America/Sao_Paulo",
        ),
        id="snapshot_fechamento_diario",
        name="Snapshot de fechamento diário (FIIs)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("🚀 [Scheduler] Scheduler iniciado. Jobs registrados:")
    for job in scheduler.get_jobs():
        logger.info(f"   📋 {job.name} → próxima execução: {job.next_run_time}")


def shutdown_scheduler():
    """Encerra o scheduler graciosamente."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("🛑 [Scheduler] Scheduler encerrado.")
