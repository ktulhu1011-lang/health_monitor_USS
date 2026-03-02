from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DataQualityIssue, FactValue, Metric, Period, Studio, SyncState
from app.services.google_sheets import parse_sheet_rows


def refresh_from_google_sheet(db: Session) -> dict:
    rows = parse_sheet_rows()

    # last-write-wins by event_time, fallback by row_index
    keyed: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        key = (row['studio_code'], row['period_code'], row['metric_code'])
        current = keyed.get(key)
        if current is None:
            keyed[key] = row
            continue
        if (row['event_time'], row['row_index']) >= (current['event_time'], current['row_index']):
            keyed[key] = row

    processed = 0
    issues = 0

    for row in keyed.values():
        studio_code = row['studio_code']
        period_code = row['period_code']
        metric_code = row['metric_code']
        raw_value = row['raw_value']

        if not studio_code or not period_code:
            _log_issue(db, 'missing_key', 'studio_code or period_code is missing', raw_value, None, None, None)
            issues += 1
            continue

        studio = _get_or_create_studio(db, studio_code, row.get('studio_name') or studio_code)
        period = _get_or_create_period(db, period_code)
        metric = _get_or_create_metric(db, metric_code, raw_value)

        value_int = None
        value_decimal = None
        if raw_value != '':
            if metric.value_type == 'int':
                try:
                    value_int = int(raw_value)
                except ValueError:
                    _log_issue(db, 'invalid_integer', f'Cannot parse integer for {metric_code}', raw_value, studio.id, period.id, metric.id)
                    issues += 1
                    continue
            else:
                try:
                    value_decimal = Decimal(raw_value)
                except InvalidOperation:
                    _log_issue(db, 'invalid_number', f'Cannot parse number for {metric_code}', raw_value, studio.id, period.id, metric.id)
                    issues += 1
                    continue

        fact = db.execute(
            select(FactValue).where(
                FactValue.studio_id == studio.id,
                FactValue.period_id == period.id,
                FactValue.metric_id == metric.id,
            )
        ).scalar_one_or_none()

        if fact is None:
            fact = FactValue(
                studio_id=studio.id,
                period_id=period.id,
                metric_id=metric.id,
                source='google_sheet',
                event_time=row['event_time'],
            )
            db.add(fact)

        fact.value_int = value_int
        fact.value_decimal = value_decimal
        fact.raw_value = raw_value
        fact.event_time = row['event_time']
        fact.updated_at = datetime.now(tz=timezone.utc)
        processed += 1

    sync_state = db.get(SyncState, 1)
    if sync_state is None:
        sync_state = SyncState(id=1)
        db.add(sync_state)
    sync_state.last_sync_at = datetime.now(tz=timezone.utc)
    sync_state.processed_rows = processed
    sync_state.quality_errors = issues

    db.commit()
    return {'processed_rows': processed, 'quality_errors': issues, 'last_sync_at': sync_state.last_sync_at}


def _get_or_create_studio(db: Session, studio_code: str, name: str) -> Studio:
    studio = db.execute(select(Studio).where(Studio.studio_code == studio_code)).scalar_one_or_none()
    if studio:
        return studio
    studio = Studio(studio_code=studio_code, name=name)
    db.add(studio)
    db.flush()
    return studio


def _get_or_create_period(db: Session, period_code: str) -> Period:
    period = db.execute(select(Period).where(Period.period_code == period_code)).scalar_one_or_none()
    if period:
        return period
    today = date.today()
    period = Period(period_code=period_code, period_type='quarter', start_date=today, end_date=today)
    db.add(period)
    db.flush()
    return period


def _infer_value_type(raw_value: str) -> str:
    if raw_value == '':
        return 'decimal'
    try:
        int(raw_value)
        return 'int'
    except ValueError:
        pass
    try:
        Decimal(raw_value)
        return 'decimal'
    except InvalidOperation:
        return 'decimal'


def _get_or_create_metric(db: Session, metric_code: str, raw_value: str) -> Metric:
    metric = db.execute(select(Metric).where(Metric.metric_code == metric_code)).scalar_one_or_none()
    if metric:
        return metric
    metric = Metric(
        metric_code=metric_code,
        name=metric_code,
        group_code='other',
        value_type=_infer_value_type(raw_value),
        unit='RUB',
        is_required=False,
    )
    db.add(metric)
    db.flush()
    return metric


def _log_issue(
    db: Session,
    issue_code: str,
    message: str,
    raw_value: str | None,
    studio_id,
    period_id,
    metric_id,
) -> None:
    db.add(
        DataQualityIssue(
            issue_code=issue_code,
            message=message,
            raw_value=raw_value,
            source='google_sheet',
            studio_id=studio_id,
            period_id=period_id,
            metric_id=metric_id,
            severity='error',
        )
    )
