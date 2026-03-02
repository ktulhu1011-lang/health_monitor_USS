from collections import defaultdict

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.db.models import DataQualityIssue, FactValue, Metric, Period, Studio, SyncState
from app.services.sync import refresh_from_google_sheet

router = APIRouter(prefix='/api/v1')


def require_api_key(x_api_key: str = Header(default='')):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail='Invalid API key')


@router.get('/healthcheck')
def healthcheck(db: Session = Depends(get_db)):
    state = db.get(SyncState, 1)
    issues_count = db.scalar(select(func.count()).select_from(DataQualityIssue))
    return {
        'status': 'ok',
        'last_sync_at': state.last_sync_at if state else None,
        'processed_rows': state.processed_rows if state else 0,
        'quality_errors': issues_count or 0,
    }


@router.get('/studios')
def list_studios(db: Session = Depends(get_db)):
    rows = db.execute(select(Studio).order_by(Studio.studio_code)).scalars().all()
    return [{'studio_code': x.studio_code, 'name': x.name, 'is_active': x.is_active} for x in rows]


@router.get('/periods')
def list_periods(db: Session = Depends(get_db)):
    rows = db.execute(select(Period).order_by(Period.period_code)).scalars().all()
    return [
        {
            'period_code': x.period_code,
            'period_type': x.period_type,
            'start_date': x.start_date,
            'end_date': x.end_date,
        }
        for x in rows
    ]


@router.get('/metrics')
def list_metrics(db: Session = Depends(get_db)):
    rows = db.execute(select(Metric).order_by(Metric.metric_code)).scalars().all()
    return [
        {
            'metric_code': x.metric_code,
            'name': x.name,
            'group_code': x.group_code,
            'value_type': x.value_type,
            'unit': x.unit,
            'is_required': x.is_required,
        }
        for x in rows
    ]


@router.get('/data')
def network_view(period_code: str = Query(...), db: Session = Depends(get_db)):
    period = db.execute(select(Period).where(Period.period_code == period_code)).scalar_one_or_none()
    if period is None:
        return {'period_code': period_code, 'items': []}

    stmt = (
        select(FactValue, Studio, Metric)
        .join(Studio, Studio.id == FactValue.studio_id)
        .join(Metric, Metric.id == FactValue.metric_id)
        .where(FactValue.period_id == period.id)
    )
    rows = db.execute(stmt).all()

    bucket = defaultdict(list)
    for fact, studio, metric in rows:
        value = fact.value_int if fact.value_int is not None else float(fact.value_decimal) if fact.value_decimal is not None else None
        bucket[studio.studio_code].append(
            {
                'metric_code': metric.metric_code,
                'value': value,
                'source': fact.source,
                'event_time': fact.event_time,
            }
        )

    items = [{'studio_code': code, 'period_code': period_code, 'values': vals} for code, vals in bucket.items()]
    return {'period_code': period_code, 'items': sorted(items, key=lambda x: x['studio_code'])}


@router.post('/refresh', dependencies=[Depends(require_api_key)])
def refresh(db: Session = Depends(get_db)):
    return refresh_from_google_sheet(db)
