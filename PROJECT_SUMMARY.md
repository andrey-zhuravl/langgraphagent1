# Резюме проекта LangGraphAgent1

## Назначение

Проект реализует AI‑агента на базе LangGraph, который планирует шаги, вызывает MCP‑инструменты и сохраняет метрики работы. Есть Telegram‑шлюз для общения с агентом и вспомогательные скрипты/демо в директории `test/`.

## Основные компоненты

### Ядро агента (LangGraph)

- **Сборка графа**: `src/lang_graph_agent/graph_builder.py` собирает `StateGraph` с узлами `planner → assistant → run_tool`, условным маршрутом после ассистента и циклом выполнения инструментов.
- **Узел планирования**: `src/lang_graph_agent/nodes/planer.py` формирует план на основе системного промпта и доступных инструментов MCP.
- **Узел ассистента**: `src/lang_graph_agent/nodes/assistant.py` выполняет текущий шаг плана, формирует вызов инструмента или финальный ответ.
- **Узел запуска инструментов**: `src/lang_graph_agent/nodes/tool_runner.py` парсит `TOOL`/`TOOL_ARG` блоки и вызывает MCP‑инструменты.
- **Состояние**: `src/lang_graph_agent/state.py` задаёт структуру `AgentState` для LangGraph.

### MCP‑инструменты

- `src/lang_graph_agent/mcp_tool/mcp_client.py` реализует клиент MCP через streamable HTTP.
- `src/lang_graph_agent/mcp_tool/mcp_bridge.py` отвечает за список инструментов, вызов и рендеринг описаний для промптов.
- `src/lang_graph_agent/utils.py` содержит безопасные вызовы LLM и MCP, а также хелпер для нормализации аргументов записи файлов.

### Метрики и БД

- Модели и DAO для PostgreSQL: `src/lang_graph_agent/metrics/models.py`, `src/lang_graph_agent/metrics/dao.py`.
- Асинхронная БД и сессии: `src/lang_graph_agent/metrics/db.py`.
- Сервис метрик: `src/lang_graph_agent/metrics/service.py`.
- Извлечение токенов из ответов LLM: `src/lang_graph_agent/metrics/extract.py`.

### Telegram‑шлюз

- Запуск бота и обработка сообщений: `src/tg/tg_gateway.py`.
- Вызов агента и форматирование ответа: `src/tg/tg_agent.py`.
- Команды `/start`, `/help`, `/reset`: `src/tg/commands.py`.
- Ограничение параллельных запросов на чат: `src/tg/locks.py`.
- Утилиты отправки сообщений и фильтр по user_id: `src/tg/tg_utils.py`.

### Визуализация

- `src/visual/to_png.py` сохраняет граф LangGraph в PNG (через Mermaid или локальный networkx/matplotlib).

### Демонстрационные скрипты

- `test/test1.py`, `test/test2.py` — примеры сборки графов и рабочих циклов с инструментами, ретраями и human‑gate.
- `test/sym_tree.py` — отдельная симуляция (не про LangGraph).

## Точки входа

- **Запуск Telegram‑бота**: `python -m src.tg.tg_gateway`.
- **Локальный запуск агента**: `src/lang_graph_agent/agent.py` — `run_once(...)`.
- `src/lang_graph_agent/__main__.py` содержит наборы заданий‑строк (не является исполняемым CLI по умолчанию).

## Настройки окружения

Обязательные или полезные переменные окружения:

- **LLM**: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `AGENT_MAX_STEPS`, `DEBUG_AGENT`.
- **MCP**: `MCP_URL`, `MCP_ALLOWED_TOOLS`.
- **Redis**: `REDIS_URL` (для чекпойнтов LangGraph).
- **Логи/отладка**: `LOG_DIR` (для `filesystem_utils`).
- **Telegram**: `TG_BOT_TOKEN`.
- **PostgreSQL**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DIALECT`.

## Зависимости

Основные зависимости перечислены в `requirements.txt`: LangGraph, langchain‑openai, MCP‑клиент, SQLAlchemy, Telegram‑бот, dotenv, tenacity и др.
