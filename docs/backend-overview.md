# Finance Analytics — Backend (visão geral)

Este documento descreve **como o backend funciona**, como rodar via Docker e um resumo do que foi implementado/ajustado nesta sessão — **sem expor dados sensíveis**.

---

## Objetivo do projeto (backend)

O backend fornece uma API para gerenciar sua carteira de FIIs:

- **Fonte de referência**: Google Sheets (planilha) para obter **Segmento** e **Valor** por **Ticker**
- **Persistência**: PostgreSQL para salvar sua posição (quantidade de cotas, preço de compra, valor total etc.)
- **Cálculos**:
  - **Valor de mercado** (atual): `quantidade_cotas * valor_cota` (valor vindo da planilha)
  - **Valor de compra**: `quantidade_cotas * valor_compra_cota` (valor informado por você)

---

## Arquitetura (como está organizado)

- **API (FastAPI)**: `backend/app/api/fundo_imobiliario.py`
  - Define os endpoints HTTP.
- **Serviços**:
  - `backend/app/services/google_sheets_service.py`
    - Integra com Google Sheets (gspread) para leitura/escrita de tickers e leitura de dados.
  - `backend/app/services/fundo_imobiliario_service.py`
    - Regras de negócio (CRUD no banco, sincronização, cálculo e salvamento da posição).
- **Modelos (SQLAlchemy)**:
  - `backend/app/models/fundo_imobiliario.py`
    - Tabela `fundos_imobiliarios`.
- **Configuração (Pydantic Settings)**:
  - `backend/app/core/config.py`
    - Lê variáveis do `.env` e extrai `spreadsheet_id` (por ID ou URL).
- **Banco**:
  - `backend/app/core/database.py`
    - Engine, sessão e uma migração leve `ensure_db_schema()` (sem Alembic).

---

## Docker (como subir)

O `docker-compose.yml` sobe:

- `db` (Postgres)
- `backend` (FastAPI/Uvicorn)

Para subir:

```bash
docker compose up -d --build
```

API:
- `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

---

## Variáveis de ambiente (sem dados sensíveis)

O Compose carrega `./backend/.env`.

Exemplo (`backend/.env.example`):

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/finance_analytics
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SHEETS_SPREADSHEET_URL=
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials/google_service_account.json
```

Notas:

- **Planilha**: você pode preencher **um** dos dois:
  - `GOOGLE_SHEETS_SPREADSHEET_ID` (recomendado), ou
  - `GOOGLE_SHEETS_SPREADSHEET_URL` (o backend extrai o ID via `/d/<id>/`).
- **Credenciais**: o arquivo `credentials/google_service_account.json` **não deve** ir para o Git.

Guia de setup: `docs/google-service-account-setup.md`.

---

## Planilha (formato esperado)

O serviço lê registros com cabeçalhos como:

- `Fundo (Ticker)`
- `Segmento`
- `Valor`

Exemplo (CSV equivalente):

```csv
Fundo (Ticker),Segmento,Valor
VGHF11,Papel / Misto (Hedge Fund),"R$ 7,06"
```

---

## Endpoints principais (backend)

Base: `/api/v1/fundos-imobiliarios`

### Saúde
- **GET** `/health`

### Banco (carteira persistida)
- **GET** `/api/v1/fundos-imobiliarios/`
  - Lista fundos salvos no Postgres (com filtros e ordenação).
- **GET** `/api/v1/fundos-imobiliarios/{fundo_id}`
  - Detalha um fundo por ID.
- **POST** `/api/v1/fundos-imobiliarios/`
  - Cria um fundo no banco (consulta a planilha para preencher segmento/valor).
- **PUT** `/api/v1/fundos-imobiliarios/{fundo_id}`
  - Atualiza (inclui `valor_compra_cota`).
- **DELETE** `/api/v1/fundos-imobiliarios/{fundo_id}`
  - Remove do banco (e tenta remover da planilha).
- **POST** `/api/v1/fundos-imobiliarios/sync-valores`
  - Atualiza `valor_cota`/`segmento` a partir da planilha para os fundos do banco.

### Planilha (somente leitura/gerenciamento de tickers)
- **GET** `/api/v1/fundos-imobiliarios/planilha`
  - Lista todos os tickers da planilha (com segmento/valor se disponíveis).
  - Se faltar `GOOGLE_SHEETS_SPREADSHEET_ID/URL`, retorna **400** com mensagem clara.
- **GET** `/api/v1/fundos-imobiliarios/planilha/{ticker}`
  - Busca um ticker na planilha e retorna `segmento` e `valor_cota`.
- **POST** `/api/v1/fundos-imobiliarios/planilha`
  - Adiciona ticker na **primeira linha vazia** da coluna A.
  - Se já existir, retorna **409**.

### Calcular e salvar posição (compra x mercado)
- **POST** `/api/v1/fundos-imobiliarios/calcular`
  - Body (exemplo):

```json
{
  "ticker": "VGHF11",
  "quantidade_cotas": 10,
  "valor_compra_cota": 7.50,
  "nome": "Opcional"
}
```

Comportamento:

- Lê da planilha: `segmento` e `valor_cota` (se disponível)
- Salva no banco:
  - `quantidade_cotas`
  - `valor_compra_cota`
  - `valor_total_compra = quantidade_cotas * valor_compra_cota`
  - `valor_total = quantidade_cotas * valor_cota` (se houver)
- É **idempotente**:
  - Se já existir no banco: **atualiza** e retorna **200**
  - Se não existir: **cria** e retorna **201**

---

## O que foi ajustado nesta sessão (resumo)

- **Docker / `.env`**
  - Garantimos o uso de `backend/.env` no `docker-compose.yml` e corrigimos o exemplo.
  - Ajustamos o `Settings` para evitar crash por variáveis extras e aceitar variações (`database_url`).
- **Rotas / conflito de path**
  - Reordenamos rotas para evitar `/{fundo_id}` capturar `/planilha`.
- **Google Sheets**
  - Adicionamos `GOOGLE_SHEETS_SPREADSHEET_ID` (opcional, recomendado).
  - Melhoramos erro quando não há ID/URL configurado (retorna 400 em vez de 500).
  - Implementamos “primeira linha vazia” e **verificação de duplicidade** na coluna A.
- **Cálculo de compra**
  - Novo campo `valor_compra_cota` e cálculo de `valor_total_compra`.
  - Migração leve sem Alembic: `ensure_db_schema()` adiciona colunas caso não existam.

---

## Segurança (boas práticas)

- Não comite:
  - `backend/.env`
  - `backend/credentials/google_service_account.json`
- Use `backend/.env.example` como referência sem segredos.

