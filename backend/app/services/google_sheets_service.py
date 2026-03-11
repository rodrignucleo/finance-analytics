import gspread
from google.oauth2.service_account import Credentials
import time
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsService:
    """Serviço para interagir com Google Sheets."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._sheet = None

    def _get_client(self) -> gspread.Client:
        """Retorna um cliente autenticado do gspread."""
        if self._client is None:
            credentials = Credentials.from_service_account_file(
                self.settings.GOOGLE_SHEETS_CREDENTIALS_FILE,
                scopes=SCOPES,
            )
            self._client = gspread.authorize(credentials)
        return self._client

    def _get_sheet(self) -> gspread.Worksheet:
        """Retorna a worksheet principal da planilha."""
        if self._sheet is None:
            spreadsheet_id = (self.settings.spreadsheet_id or "").strip()
            if not spreadsheet_id:
                raise ValueError(
                    "Configuração ausente: defina GOOGLE_SHEETS_SPREADSHEET_ID ou GOOGLE_SHEETS_SPREADSHEET_URL no .env"
                )
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_id)
            self._sheet = spreadsheet.sheet1
        return self._sheet

    def adicionar_ticker(self, ticker: str) -> int:
        """
        Adiciona um ticker na próxima linha vazia da coluna A.
        Retorna o número da linha onde foi inserido.
        """
        sheet = self._get_sheet()

        # Pega todos os valores da coluna A para encontrar a próxima linha vazia
        col_a_values = sheet.col_values(1)
        next_row = len(col_a_values) + 1

        # Insere o ticker na coluna A da próxima linha vazia
        sheet.update_cell(next_row, 1, ticker)

        logger.info(f"Ticker {ticker} adicionado na linha {next_row} da planilha.")
        return next_row

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        return (ticker or "").strip().upper()

    def procurar_linha_ticker(self, ticker: str) -> int | None:
        """Retorna a linha (1-index) onde o ticker existe na coluna A, ou None."""
        sheet = self._get_sheet()
        target = self._normalize_ticker(ticker)
        if not target:
            return None

        col_a_values = sheet.col_values(1)
        for idx, value in enumerate(col_a_values, start=1):
            if self._normalize_ticker(value) == target:
                return idx
        return None

    def adicionar_ticker_primeira_linha_vazia(self, ticker: str) -> tuple[int, bool]:
        """
        Adiciona um ticker na primeira linha vazia da coluna A.
        Se já existir na coluna A, não adiciona e retorna (linha_existente, False).
        Retorna (linha, created).
        """
        sheet = self._get_sheet()
        normalized = self._normalize_ticker(ticker)
        if not normalized:
            raise ValueError("Ticker vazio.")

        # 1) Se já existir, retorna a linha existente
        existing_row = self.procurar_linha_ticker(normalized)
        if existing_row:
            logger.info(f"Ticker {normalized} já existe na planilha (linha {existing_row}).")
            return existing_row, False

        # 2) Encontra a primeira linha vazia considerando possíveis 'buracos'
        # col_values pode não incluir células vazias; por isso buscamos uma janela.
        col_a_values = sheet.col_values(1)
        scan_len = max(len(col_a_values) + 50, 50)
        col_a_range = sheet.get(f"A1:A{scan_len}")
        # sheet.get retorna lista de listas; pode vir com linhas faltando no final
        for row in range(1, scan_len + 1):
            value = ""
            if row - 1 < len(col_a_range) and col_a_range[row - 1]:
                value = col_a_range[row - 1][0]
            if not str(value).strip():
                sheet.update_cell(row, 1, normalized)
                logger.info(f"Ticker {normalized} adicionado na linha {row} da planilha.")
                return row, True

        # fallback (praticamente nunca)
        next_row = len(col_a_values) + 1
        sheet.update_cell(next_row, 1, normalized)
        logger.info(f"Ticker {normalized} adicionado na linha {next_row} da planilha (fallback).")
        return next_row, True

    def obter_dados_por_ticker(self, ticker: str, max_retries: int = 5, delay: float = 3.0) -> dict:
        """Busca um ticker na coluna A e retorna dados (segmento, valor)."""
        normalized = self._normalize_ticker(ticker)
        row = self.procurar_linha_ticker(normalized)
        if not row:
            raise ValueError(f"Ticker {normalized} não encontrado na planilha.")
        return self.obter_dados_ticker(normalized, row, max_retries=max_retries, delay=delay)

    def obter_dados_ticker(self, ticker: str, row: int, max_retries: int = 5, delay: float = 3.0) -> dict:
        """
        Obtém os dados (segmento e valor) de um ticker na planilha.
        Faz retries pois o Google Finance pode demorar a atualizar os valores.
        """
        sheet = self._get_sheet()

        for attempt in range(max_retries):
            row_values = sheet.row_values(row)

            # Verifica se as colunas B (segmento) e C (valor) já foram preenchidas
            if len(row_values) >= 3 and row_values[1] and row_values[2]:
                segmento = row_values[1].strip()
                valor_str = row_values[2].strip()
                valor = self._parse_valor(valor_str)

                logger.info(f"Dados obtidos para {ticker}: segmento={segmento}, valor={valor}")
                return {
                    "ticker": ticker,
                    "segmento": segmento,
                    "valor_cota": valor,
                }

            logger.info(f"Tentativa {attempt + 1}/{max_retries}: Dados ainda não disponíveis para {ticker}")
            time.sleep(delay)

        # Se não conseguiu obter os dados após todas as tentativas, retorna com valores None
        logger.warning(f"Não foi possível obter dados completos para {ticker} após {max_retries} tentativas")
        row_values = sheet.row_values(row)
        return {
            "ticker": ticker,
            "segmento": row_values[1].strip() if len(row_values) >= 2 and row_values[1] else None,
            "valor_cota": self._parse_valor(row_values[2]) if len(row_values) >= 3 and row_values[2] else None,
        }

    def remover_ticker(self, ticker: str) -> bool:
        """Remove um ticker da planilha."""
        sheet = self._get_sheet()

        try:
            cell = sheet.find(ticker)
            if cell:
                # Limpa a linha inteira
                sheet.delete_rows(cell.row)
                logger.info(f"Ticker {ticker} removido da planilha (linha {cell.row}).")
                return True
        except gspread.exceptions.CellNotFound:
            logger.warning(f"Ticker {ticker} não encontrado na planilha.")

        return False

    def atualizar_valor_ticker(self, ticker: str) -> dict | None:
        """Busca e retorna os dados atualizados de um ticker na planilha."""
        sheet = self._get_sheet()

        try:
            cell = sheet.find(ticker)
            if cell:
                return self.obter_dados_ticker(ticker, cell.row, max_retries=2, delay=1.0)
        except gspread.exceptions.CellNotFound:
            logger.warning(f"Ticker {ticker} não encontrado na planilha.")

        return None

    def obter_todos_dados(self) -> list[dict]:
        """Obtém todos os dados da planilha."""
        sheet = self._get_sheet()
        records = sheet.get_all_records()

        result = []
        for record in records:
            ticker = record.get("Fundo (Ticker)", "")
            segmento = record.get("Segmento", "")
            valor_str = str(record.get("Valor", ""))

            if ticker:
                result.append({
                    "ticker": ticker.strip(),
                    "segmento": segmento.strip() if segmento else None,
                    "valor_cota": self._parse_valor(valor_str) if valor_str else None,
                })

        return result

    @staticmethod
    def _parse_valor(valor_str: str) -> float | None:
        """Converte string de valor monetário para float."""
        if not valor_str:
            return None

        try:
            # Remove "R$", espaços e pontos de milhar, troca vírgula por ponto
            cleaned = valor_str.replace("R$", "").strip()
            cleaned = cleaned.replace(" ", "")

            # Verifica se usa formato brasileiro (1.234,56) ou americano (1,234.56)
            if "," in cleaned and "." in cleaned:
                # Formato brasileiro: remove pontos de milhar, troca vírgula por ponto
                if cleaned.rindex(",") > cleaned.rindex("."):
                    cleaned = cleaned.replace(".", "").replace(",", ".")
                # Formato americano: remove vírgulas de milhar
                else:
                    cleaned = cleaned.replace(",", "")
            elif "," in cleaned:
                cleaned = cleaned.replace(",", ".")

            return float(cleaned)
        except (ValueError, AttributeError):
            logger.warning(f"Não foi possível converter valor: {valor_str}")
            return None


def get_google_sheets_service() -> GoogleSheetsService:
    """Factory para o serviço do Google Sheets."""
    return GoogleSheetsService()
