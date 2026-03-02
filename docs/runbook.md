# Runbook (MVP)

## Базовые операции

- Рекомендуемый интервал sync: каждые 10–30 минут.
- В MVP реализован ручной refresh через `POST /api/v1/refresh` (с `X-API-Key`).

## Где смотреть состояние

1. `GET /api/v1/healthcheck`
   - `last_sync_at`
   - `processed_rows`
   - `quality_errors`

2. Таблица `data_quality_issues`
   - ошибки валидации/парсинга
   - проблемы с обязательными ключами

## Типовые проблемы

- Пустой результат `/data`:
  - проверьте `period_code`
  - убедитесь, что `refresh` был выполнен успешно

- Ошибки refresh:
  - проверьте доступность `GOOGLE_SHEET_URL` (или корректность `GOOGLE_SHEET_ID/GID`)
  - проверьте, что таблица опубликована для чтения (если используется CSV export)

- Рост ошибок качества:
  - проверьте формат числовых колонок в Google Sheet
  - проверьте заполненность `studio_code` и `period_code`
