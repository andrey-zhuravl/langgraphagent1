# Резюме проекта LangGraphAgent1

## Назначение и общий обзор

Проект реализует AI‑агента на базе LangGraph, который:

- планирует шаги выполнения задачи,
- вызывает MCP‑инструменты (через HTTP‑клиент),
- ведёт сбор метрик (в БД),
- интегрируется с Telegram для диалогов с пользователем,
- умеет сохранять визуализацию графа исполнения.

Код в `src/` организован как несколько пакетов:

- `lang_graph_agent` — основная логика агента и его графа,
- `tg` — Telegram‑шлюз для общения,
- `visual` — утилита отрисовки графов,
- `test` — демонстрационные/экспериментальные скрипты.

## Архитектура агента (LangGraph)

### Сборка графа

`src/lang_graph_agent/graph_builder.py` собирает `StateGraph` со следующими узлами и рёбрами:

```
START → planner → assistant → (run_tool | END)
run_tool → assistant
```

- `planner` — строит план действий (строки), указывает инструмент на каждом шаге.
- `assistant` — на каждом шаге либо формирует вызов инструмента, либо финальный ответ.
- `run_tool` — парсит вызовы инструмента и вызывает MCP‑сервер.

Внутренний цикл `assistant → run_tool → assistant` позволяет выполнять несколько инструментов последовательно до достижения `FINAL` или лимита шагов.

### Состояние агента

`src/lang_graph_agent/state.py` описывает `AgentState`. Важно помнить:

- `messages` — история сообщений LangChain (накапливается для контекста).
- `plan`/`tools` — результат планирования (список шагов и соответствующих инструментов).
- `tools_used` — список реально использованных инструментов (для метрик).
- `llm_usage_events` — события по токенам и узлам.
- `current_step`, `steps`, `llm_calls` — счетчики прогресса.

### Планировщик

`src/lang_graph_agent/nodes/planer.py`:

- берёт последний пользовательский запрос,
- формирует системный промпт из `prompts/plan_prompt.py`,
- вызывает LLM (через `safe_invoke`),
- парсит результат функцией `plan_parse`.

Формат ожидаемого плана:

```
PLAN:
1. <описание шага1>===<tool_name1>
2. <описание шага2>===<tool_name2>
```

### Ассистент

`src/lang_graph_agent/nodes/assistant.py`:

- берёт шаг по индексу `current_step`,
- формирует промпт из `prompts/assistant_prompt.py`,
- если достигнут `max_steps`, форсирует `FINAL` без инструментов,
- сохраняет промпты и ответы в `LOG_DIR/<debug_dir>`.

Ожидаемый формат вызова инструмента:

```
TOOL: {"name":"<tool_name>"}
TOOL_ARG=<arg1>:
<значение>
TOOL_ARG=<arg2>:
<значение>
```

### Запуск инструментов

`src/lang_graph_agent/nodes/tool_runner.py`:

- парсит все `TOOL`/`TOOL_ARG` блоки,
- валидирует имя инструмента против `mcp_tool_names`,
- вызывает MCP‑инструмент через `safe_call_tool`,
- возвращает результат в `SystemMessage` в виде `TOOL_RESULT_BATCH`.

Если формат запроса неверный, формирует ошибку и просит ассистента повторить формат.

## MCP‑инструменты и интеграция

### MCP‑клиент

`src/lang_graph_agent/mcp_tool/mcp_client.py` реализует:

- `list_tools` — получение доступных инструментов,
- `call_tool` — вызов инструмента по имени с аргументами,
- работу через streamable HTTP клиента MCP.

### MCP‑мост

`src/lang_graph_agent/mcp_tool/mcp_bridge.py`:

- оборачивает инструменты для LLM,
- фильтрует и рендерит список инструментов в текст,
- предоставляет `safe_list_tools` и `call_tool_sync`.

### Утилиты LLM/MCP

`src/lang_graph_agent/utils.py`:

- `safe_invoke` — повторные вызовы LLM (retry на `APIConnectionError`),
- `safe_call_tool` — retry для вызова инструмента,
- `_adapt_write_file_args` — нормализует контент (base64, sha256, исправление "\\n").

## Метрики и база данных

### Модели и DAO

- `src/lang_graph_agent/metrics/models.py`:
  - `Task` — задачи агента,
  - `TokenUsage` — статистика токенов.
- `src/lang_graph_agent/metrics/dao.py`:
  - создание задачи и финализация (`finish_task`),
  - вставка токен‑метрик.

### Сессии и движок

`src/lang_graph_agent/metrics/db.py` настраивает `AsyncEngine` и `SESSION_FACTORY` на PostgreSQL через env‑переменные.

### Сервис метрик

`src/lang_graph_agent/metrics/service.py`:

- создаёт задачи,
- сохраняет usage‑события,
- завершает задачи со статусом `success`/`error`.

### Извлечение токенов

`src/lang_graph_agent/metrics/extract.py`:

- работает с `usage_metadata` (LangChain формат) и `response_metadata` (OpenAI‑совместимый формат),
- формирует структуры `event` для сохранения.

## Telegram‑шлюз

### Основной вход

`src/tg/tg_gateway.py`:

- запускает long polling бот (`python -m src.tg.tg_gateway`),
- обрабатывает команды и текстовые сообщения,
- ограничивает параллельные вызовы через `chat_lock`.

### Вызов агента

`src/tg/tg_agent.py`:

- подготавливает `debug_dir`,
- создаёт задачу в метриках (`create_agent_task`),
- вызывает `run_once` агента,
- сохраняет метрики (`finalize_task_and_usage`),
- возвращает пользователю `FINAL` ответ.

### Утилиты и команды

- `src/tg/commands.py`: `/start`, `/help`, `/reset`.
- `src/tg/tg_utils.py`: проверка `ALLOWED_USER_IDS`, разбиение длинных сообщений.
- `src/tg/locks.py`: `asyncio.Lock` на чат.

## Визуализация графа

`src/visual/to_png.py`:

- `save_langgraph_png1` — Mermaid + pyppeteer,
- `save_langgraph_png2` — локальный рендер через `networkx` и `matplotlib`.

## Демонстрационные скрипты

### `test/test1.py`

- Минимальный граф с узлами `assistant → run_tool`.
- Демонстрирует переходы и ошибки, имитацию нестабильного инструмента.

### `test/test2.py`

- Более сложный пример с `planner`, `executor`, `critic`, `retry`.
- Демонстрирует human‑gate и повторные попытки инструмента.
- Сохраняет PNG графа (`graph.png`).

### `test/sym_tree.py`

- Несвязанный с LangGraph симулятор (лес и жуки).

## Точки входа и сценарии запуска

- **Telegram‑бот**: `python -m src.tg.tg_gateway`.
- **Запуск агента из Python**: `src/lang_graph_agent/agent.py` → `run_once(...)`.
- **Генерация PNG**: вызов `save_langgraph_png1` или `save_langgraph_png2`.

Файл `src/lang_graph_agent/__main__.py` содержит набор текстовых задач‑примеров (не CLI).

## Настройки окружения

### LLM

- `OPENAI_BASE_URL` — base URL API.
- `OPENAI_API_KEY` — ключ.
- `OPENAI_MODEL` — модель.
- `AGENT_MAX_STEPS` — лимит шагов.
- `DEBUG_AGENT` — логирование.

### MCP

- `MCP_URL` — адрес MCP‑сервера.
- `MCP_ALLOWED_TOOLS` — ограничение инструментов (CSV).

### Redis (checkpointer)

- `REDIS_URL` — подключение для `AsyncRedisSaver`.

### Логи

- `LOG_DIR` — директория для `filesystem_utils`.

### Telegram

- `TG_BOT_TOKEN` — токен бота.

### PostgreSQL

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DIALECT`.

## Зависимости

`requirements.txt` включает: LangGraph, langchain‑openai, langchain‑core, MCP‑клиент, dotenv, tenacity, SQLAlchemy, pydantic, python‑telegram‑bot, openai и др.

## Ключевые особенности и ограничения

- Планировщик требует строго заданный формат плана, иначе парсер будет некорректен.
- Ассистент и инструментальная нода завязаны на формат `TOOL`/`TOOL_ARG`.
- Чекпоинты LangGraph требуют Redis.
- Метрики требуют PostgreSQL; без него агент может не запускаться в прод‑режиме.
- `filesystem_utils` ориентирован на Windows‑подобные пути с `\`.
