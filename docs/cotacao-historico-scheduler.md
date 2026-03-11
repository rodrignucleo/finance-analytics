# Cotação Histórico — Scheduler de Fechamento

Documentação do scheduler automático que coleta cotações de fechamento diárias dos FIIs da planilha do Google Sheets.

---

## Tabela: `cotacao_historico`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | Integer (PK) | Identificador auto-incremento |
| `ticker` | String(10) | Símbolo do fundo (ex: `VGHF11`) |
| `segmento` | String(100) | Segmento do fundo |
| `valor_fechamento` | Float | Valor de fechamento do dia |
| `data_referencia` | Date | Data do pregão |
| `created_at` | DateTime | Quando foi salvo |

> Constraint **UNIQUE** em `(ticker, data_referencia)` — impede duplicatas do mesmo ticker no mesmo dia.

---

## Scheduler (Cron Job)

- **Tecnologia**: `APScheduler` com `AsyncIOScheduler` (integrado ao event loop do FastAPI)
- **Horário**: **18:00 (America/Sao_Paulo)**, de **segunda a sexta**
- O mercado da B3 fecha às 17:30 — rodamos 30 min depois para garantir que os valores na planilha já foram atualizados
- O `TZ=America/Sao_Paulo` foi adicionado ao `docker-compose.yml` para garantir o fuso correto

### Fluxo do job

1. Lê **todos os tickers da planilha** do Google Sheets (não só os que estão no portfólio)
2. Para cada ticker, salva `ticker`, `segmento`, `valor_fechamento` e `data_referencia` na tabela `cotacao_historico`
3. Se já existir registro para o mesmo ticker+data, **atualiza** em vez de duplicar
4. Loga detalhes de cada ticker salvo/atualizado/com erro

---

## Endpoints

Base: `/api/v1/cotacoes-historico`

### Listar cotações históricas

- **GET** `/api/v1/cotacoes-historico/`
  - Filtros: `ticker`, `data_inicio`, `data_fim`
  - Ordenação: `order_by` (ticker, data_referencia, valor_fechamento, segmento) + `order_direction` (asc/desc)

### Histórico de um ticker

- **GET** `/api/v1/cotacoes-historico/{ticker}`
  - Retorna todo o histórico de cotações de um ticker específico, ordenado por data (mais recente primeiro).

### Snapshot manual

- **POST** `/api/v1/cotacoes-historico/snapshot`
  - Parâmetro opcional: `data_referencia` (YYYY-MM-DD). Se não informado, usa a data de hoje.
  - Executa a coleta manualmente — útil para testar ou salvar valores de uma data específica.

---

## Arquivos envolvidos

| Arquivo | Descrição |
|---------|-----------|
| `app/models/cotacao_historico.py` | Model SQLAlchemy da tabela |
| `app/schemas/cotacao_historico.py` | Schemas Pydantic (request/response) |
| `app/services/cotacao_historico_service.py` | Lógica de snapshot + queries de histórico |
| `app/core/scheduler.py` | Configuração do APScheduler + job de fechamento |
| `app/api/cotacao_historico.py` | Endpoints REST |

---

## Como testar

1. Reconstrua os containers:

```bash
docker compose up -d --build
```

2. Acesse o Swagger: `http://localhost:8000/docs`

3. Use o endpoint **POST** `/api/v1/cotacoes-historico/snapshot` para executar o snapshot manualmente e verificar o funcionamento.

4. Consulte os dados com **GET** `/api/v1/cotacoes-historico/` ou **GET** `/api/v1/cotacoes-historico/{ticker}`.
