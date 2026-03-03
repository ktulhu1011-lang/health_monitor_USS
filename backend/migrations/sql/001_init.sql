create extension if not exists "uuid-ossp";

create table if not exists studios (
  id uuid primary key,
  studio_code text unique not null,
  name text not null,
  is_active boolean not null default true
);

create table if not exists periods (
  id uuid primary key,
  period_code text unique not null,
  period_type text not null,
  start_date date not null,
  end_date date not null
);

create table if not exists metrics (
  id uuid primary key,
  metric_code text unique not null,
  name text not null,
  group_code text not null,
  value_type text not null,
  unit text,
  is_required boolean not null default false
);

create table if not exists fact_values (
  id uuid primary key,
  studio_id uuid not null references studios(id),
  period_id uuid not null references periods(id),
  metric_id uuid not null references metrics(id),
  value_decimal numeric(20,6),
  value_int integer,
  raw_value text,
  source text not null,
  event_time timestamptz not null,
  updated_at timestamptz not null default now(),
  constraint uq_fact_values_key unique (studio_id, period_id, metric_id)
);

create table if not exists data_quality_issues (
  id uuid primary key,
  studio_id uuid references studios(id),
  period_id uuid references periods(id),
  metric_id uuid references metrics(id),
  severity text not null,
  issue_code text not null,
  message text not null,
  raw_value text,
  detected_at timestamptz not null default now(),
  source text not null
);

create table if not exists sync_state (
  id integer primary key,
  last_sync_at timestamptz,
  processed_rows integer not null default 0,
  quality_errors integer not null default 0
);
