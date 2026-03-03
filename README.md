# Информационный монитор «Здоровье УСС»

MVP Iteration 1: FastAPI + PostgreSQL + синхронизация данных из Google Sheets (CSV export).

## Что уже реализовано

- Backend API на FastAPI (`/backend`).
- PostgreSQL хранение справочников, витрины и журнала качества данных.
- Ручной `POST /api/v1/refresh` (защита `X-API-Key`) для загрузки Google Sheets.
- Read endpoints:
  - `GET /api/v1/healthcheck`
  - `GET /api/v1/studios`
  - `GET /api/v1/periods`
  - `GET /api/v1/metrics`
  - `GET /api/v1/data?period_code=...`
- SQL-миграция MVP в `backend/migrations/sql/001_init.sql`.

## Как запустить локально

1. Скопируйте переменные окружения:

```bash
cp .env.example .env
```

2. Заполните `.env` минимум следующими параметрами:

- `DATABASE_URL` (по умолчанию уже настроен под docker-compose)
- `API_KEY`
- `GOOGLE_SHEET_URL` **или** (`GOOGLE_SHEET_ID` + `GOOGLE_SHEET_GID`)

По умолчанию в `.env.example` уже указан рабочий CSV-URL предоставленной Google-таблицы.

3. Запустите сервисы:

```bash
docker compose up --build
```

Backend будет доступен на `http://localhost:8000`.

## Формат Google Sheet (MVP)

Ожидается wide-формат экспорта Google Forms/Sheets:

- `Название УСС` → `studio_name`
- `Отчетный период` → нормализованный `period_code` (`2026-02`, `Февраль 2026`, `Q1 2026`, `1 квартал 2026`)
- `Отметка времени`/`Timestamp` (если есть) → `event_time`
- `Электронная почта` игнорируется
- остальные поддержанные русские колонки маппятся на фиксированные `metric_code`

`studio_code` вычисляется детерминированно из `Название УСС`: транслитерация → UPPERCASE → `_`-разделители.
Каждая строка превращается в набор метрик (long-format внутри sync).

## Правила обработки

- Last-write-wins по ключу `(studio_code, period_code, metric_code)`.
- Приоритет выбора последней записи:
  1. максимальный `timestamp`/`updated_at`
  2. если timestamp отсутствует/невалиден — порядок строк (последняя строка выигрывает)
- Студии/периоды/метрики создаются автоматически при первом появлении.
- Ошибки качества данных пишутся в `data_quality_issues` и не останавливают синхронизацию.

## Примеры вызовов API

Проверка здоровья:

```bash
curl http://localhost:8000/api/v1/healthcheck
```

Ручной refresh:

```bash
curl -X POST http://localhost:8000/api/v1/refresh \
  -H "X-API-Key: $API_KEY"
```

Витрина за период:

```bash
curl "http://localhost:8000/api/v1/data?period_code=2026Q1"
```

## Структура репозитория

- `docker-compose.yml` — запуск Postgres и backend.
- `.env.example` — пример конфигурации среды.
- `backend/app` — код FastAPI, DB и сервисы синхронизации.
- `backend/migrations/sql` — SQL-миграции MVP.
- `docs/data_model.md` — логическая модель данных.
- `docs/runbook.md` — краткий operational runbook.
- `openapi/v1.yaml` — API-контракт v1.
