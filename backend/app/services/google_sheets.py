from __future__ import annotations

from datetime import datetime, timezone
import csv
import io

import requests

from app.config import settings

SYSTEM_COLUMNS = {'timestamp', 'updated_at', 'studio_code', 'studio_name', 'period_code'}


def _build_sheet_url() -> str:
    if settings.google_sheet_url:
        return settings.google_sheet_url
    if settings.google_sheet_id:
        gid = settings.google_sheet_gid or '0'
        return f'https://docs.google.com/spreadsheets/d/{settings.google_sheet_id}/export?format=csv&gid={gid}'
    raise ValueError('Google sheet config is empty. Set GOOGLE_SHEET_URL or GOOGLE_SHEET_ID.')


def parse_sheet_rows() -> list[dict]:
    url = _build_sheet_url()
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text))
    normalized: list[dict] = []
    for idx, row in enumerate(reader):
        ts_raw = (row.get('timestamp') or row.get('updated_at') or '').strip()
        event_time = _parse_ts(ts_raw) or datetime.now(tz=timezone.utc)
        base = {
            'studio_code': (row.get('studio_code') or '').strip(),
            'studio_name': (row.get('studio_name') or '').strip(),
            'period_code': (row.get('period_code') or '').strip(),
            'event_time': event_time,
            'row_index': idx,
        }
        for key, val in row.items():
            if not key:
                continue
            metric_code = key.strip()
            if metric_code in SYSTEM_COLUMNS:
                continue
            normalized.append({
                **base,
                'metric_code': metric_code,
                'raw_value': (val or '').strip(),
            })
    return normalized


def _parse_ts(ts_raw: str) -> datetime | None:
    if not ts_raw:
        return None
    try:
        return datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
    except ValueError:
        return None
