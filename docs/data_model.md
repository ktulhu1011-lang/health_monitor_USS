# Модель данных «Здоровье УСС» (MVP)

## 1) Справочники

### `studios`

| Поле | Тип | Ограничения |
|---|---|---|
| id | uuid | PK |
| studio_code | text | UNIQUE, NOT NULL |
| name | text | NOT NULL |
| is_active | boolean | DEFAULT true |

### `periods`

| Поле | Тип | Ограничения |
|---|---|---|
| id | uuid | PK |
| period_code | text | UNIQUE, NOT NULL |
| period_type | text | NOT NULL (`month`/`quarter`) |
| start_date | date | NOT NULL |
| end_date | date | NOT NULL |

### `metrics`

| Поле | Тип | Ограничения |
|---|---|---|
| id | uuid | PK |
| metric_code | text | UNIQUE, NOT NULL |
| name | text | NOT NULL |
| group_code | text | NOT NULL (`finance`/`portfolio`/`kpi`) |
| value_type | text | NOT NULL (`int`/`decimal`) |
| unit | text | NULL |
| is_required | boolean | DEFAULT false |
| rules_json | jsonb | NULL |

## 2) Витрина

### `fact_values`

| Поле | Тип | Ограничения |
|---|---|---|
| id | uuid | PK |
| studio_id | uuid | FK -> `studios.id`, NOT NULL |
| period_id | uuid | FK -> `periods.id`, NOT NULL |
| metric_id | uuid | FK -> `metrics.id`, NOT NULL |
| value_decimal | numeric(20,6) | NULL |
| value_int | bigint | NULL |
| source | text | NOT NULL (`google_sheet`/`api`) |
| event_time | timestamptz | NOT NULL |
| updated_at | timestamptz | NOT NULL |

Уникальность витрины:

```sql
UNIQUE (studio_id, period_id, metric_id)
```

## 3) Качество данных

### `data_quality_issues`

| Поле | Тип | Ограничения |
|---|---|---|
| id | uuid | PK |
| studio_id | uuid | FK -> `studios.id` |
| period_id | uuid | FK -> `periods.id` |
| metric_id | uuid | FK -> `metrics.id`, NULLABLE |
| severity | text | NOT NULL (`warning`/`error`) |
| issue_code | text | NOT NULL |
| message | text | NOT NULL |
| raw_value | text | NULL |
| detected_at | timestamptz | NOT NULL |
| source | text | NOT NULL (`google_sheet`/`api`) |

## 4) Аудит API-входов (опционально)

### `ingest_events`

| Поле | Тип | Ограничения |
|---|---|---|
| id | uuid | PK |
| source | text | NOT NULL (`api`) |
| studio_code | text | NOT NULL |
| period_code | text | NOT NULL |
| event_time | timestamptz | NOT NULL |
| force | boolean | DEFAULT false |
| comment | text | NULL |
| created_at | timestamptz | NOT NULL |

## 5) DDL-каркас

```sql
create table if not exists studios (
  id uuid primary key,
  studio_code text unique not null,
  name text not null,
  is_active boolean not null default true
);

create table if not exists periods (
  id uuid primary key,
  period_code text unique not null,
  period_type text not null check (period_type in ('month', 'quarter')),
  start_date date not null,
  end_date date not null
);

create table if not exists metrics (
  id uuid primary key,
  metric_code text unique not null,
  name text not null,
  group_code text not null check (group_code in ('finance', 'portfolio', 'kpi')),
  value_type text not null check (value_type in ('int', 'decimal')),
  unit text,
  is_required boolean not null default false,
  rules_json jsonb
);

create table if not exists fact_values (
  id uuid primary key,
  studio_id uuid not null references studios(id),
  period_id uuid not null references periods(id),
  metric_id uuid not null references metrics(id),
  value_decimal numeric(20,6),
  value_int bigint,
  source text not null check (source in ('google_sheet', 'api')),
  event_time timestamptz not null,
  updated_at timestamptz not null,
  unique (studio_id, period_id, metric_id)
);

create table if not exists data_quality_issues (
  id uuid primary key,
  studio_id uuid references studios(id),
  period_id uuid references periods(id),
  metric_id uuid references metrics(id),
  severity text not null check (severity in ('warning', 'error')),
  issue_code text not null,
  message text not null,
  raw_value text,
  detected_at timestamptz not null,
  source text not null check (source in ('google_sheet', 'api'))
);
```
