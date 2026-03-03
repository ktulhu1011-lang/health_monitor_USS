from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime, timezone

import requests

from app.config import settings

logger = logging.getLogger(__name__)

EMAIL_HEADERS = {'Электронная почта', 'Email Address'}
TIMESTAMP_HEADERS = {'Отметка времени', 'Timestamp', 'timestamp', 'updated_at'}
STUDIO_HEADER = 'Название УСС'
PERIOD_HEADER = 'Отчетный период'

# explicit mapping for current Google Forms export columns
METRIC_HEADER_TO_CODE = {
    'Операционные расходы за период (руб)': 'opex_spent_period_rub',
    'Остаток средств на операционные расходы (руб)': 'opex_balance_end_rub',
    'Остаток инвестиционных средств (руб)': 'investment_balance_end_rub',
    'Сколько проинвестировано в стартапы – первые этапы (руб)': 'invested_first_stage_rub',
    'Сколько проинвестировано в стартапы – 2+ этапы (руб)': 'invested_follow_on_rub',
    'Количество стартапов в портфеле УСС': 'portfolio_startups_count',
    'Сколько проектов заморожено за отчетный период': 'frozen_projects_period_count',
    'Количество проектов на 1 этапе': 'projects_stage_1_count',
    'Количество проектов на 2 этапе': 'projects_stage_2_count',
    'Количество проектов на 3 этапе': 'projects_stage_3_count',
    'Количество проектов на 4 этапе': 'projects_stage_4_count',
    'Сколько РИДов получено за период': 'rids_period_count',
    'Сколько внебюджетных средств привлечено за отчетный период': 'off_budget_raised_period_rub',
    'Сколько стартапов выполнили требования для первичного получения статуса МТК за отчетный период': 'mtk_primary_status_period_count',
}

INT_METRICS = {
    'portfolio_startups_count',
    'frozen_projects_period_count',
    'projects_stage_1_count',
    'projects_stage_2_count',
    'projects_stage_3_count',
    'projects_stage_4_count',
    'rids_period_count',
    'mtk_primary_status_period_count',
}

RUS_MONTHS = {
    'январь': '01', 'февраль': '02', 'март': '03', 'апрель': '04',
    'май': '05', 'июнь': '06', 'июль': '07', 'август': '08',
    'сентябрь': '09', 'октябрь': '10', 'ноябрь': '11', 'декабрь': '12',
    'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
    'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
    'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12',
}

TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
    'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def _build_sheet_url() -> str:
    if settings.google_sheet_url:
        return settings.google_sheet_url
    if settings.google_sheet_id:
        gid = settings.google_sheet_gid or '0'
        return f'https://docs.google.com/spreadsheets/d/{settings.google_sheet_id}/export?format=csv&gid={gid}'
    raise ValueError('Google sheet config is empty. Set GOOGLE_SHEET_URL or GOOGLE_SHEET_ID.')


def derive_studio_code(studio_name: str) -> str:
    raw_name = _normalize_token(studio_name)
    raw = ''.join(TRANSLIT.get(ch.lower(), ch) for ch in raw_name)
    raw = raw.upper()
    raw = re.sub(r'[^A-Z0-9]+', '_', raw)
    raw = re.sub(r'_+', '_', raw).strip('_')
    return raw[:64]


def normalize_period(period_raw: str) -> tuple[str | None, str | None]:
    value = _normalize_token(period_raw)
    if not value:
        return None, None

    if re.match(r'^\d{4}-(0[1-9]|1[0-2])$', value):
        return value, 'month'

    m = re.match(r'^(\d{4})\.(0[1-9]|1[0-2])$', value)
    if m:
        return f'{m.group(1)}-{m.group(2)}', 'month'

    m = re.match(r'^([1-9]|1[0-2])\.(\d{4})$', value)
    if m:
        return f'{m.group(2)}-{int(m.group(1)):02d}', 'month'

    m = re.match(r'^(Q([1-4]))\s+(\d{4})$', value, flags=re.IGNORECASE)
    if m:
        return f'{m.group(3)}Q{m.group(2)}', 'quarter'

    m = re.match(r'^([1-4])\s+квартал\s+(\d{4})$', value, flags=re.IGNORECASE)
    if m:
        return f'{m.group(2)}Q{m.group(1)}', 'quarter'

    m = re.match(r'^([А-Яа-яA-Za-z]+)\s+(\d{4})$', value)
    if m:
        month = RUS_MONTHS.get(m.group(1).lower())
        if month:
            return f'{m.group(2)}-{month}', 'month'

    return None, None


def parse_sheet_rows() -> dict:
    url = _build_sheet_url()
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    csv_reader = csv.reader(io.StringIO(response.text))
    raw_headers = next(csv_reader, [])
    normalized_headers = [_normalize_token(h) for h in raw_headers]

    idx_studio = _find_header_index_any(normalized_headers, [STUDIO_HEADER, 'Название УСС '])
    idx_period = _find_header_index_any(normalized_headers, [PERIOD_HEADER, 'Отчетный период '])
    idx_ts = _find_first_header_index(normalized_headers, TIMESTAMP_HEADERS)

    metric_indices: list[tuple[int, str, str]] = []
    for header_ru, metric_code in METRIC_HEADER_TO_CODE.items():
        idx = _find_header_index(normalized_headers, header_ru)
        if idx is not None:
            metric_indices.append((idx, header_ru, metric_code))

    normalized_rows: list[dict] = []
    issues: list[dict] = []

    for idx, row in enumerate(csv_reader):
        raw_studio_cell = _cell(row, idx_studio)
        studio_name = _normalize_token(raw_studio_cell)
        studio_code = derive_studio_code(studio_name) if studio_name else ''

        raw_period_cell = _cell(row, idx_period)
        period_raw = _normalize_token(raw_period_cell)
        period_code, period_type = normalize_period(period_raw)

        ts_raw = _normalize_token(_cell(row, idx_ts))
        parsed_ts = _parse_ts(ts_raw)
        event_time = parsed_ts or datetime(1970, 1, 1, tzinfo=timezone.utc)

        if idx < 3:
            logger.debug(
                'row_debug idx=%s headers=%r idx_studio=%r studio_raw=%r period_raw=%r',
                idx,
                normalized_headers,
                idx_studio,
                raw_studio_cell,
                raw_period_cell,
            )

        if not studio_name:
            issue = {
                'issue_code': 'missing_studio',
                'message': f'Missing studio name in column {STUDIO_HEADER}',
                'raw_value': raw_studio_cell,
                'row_index': idx,
            }
            issues.append(issue)
            logger.warning('sync_issue: %s', issue)
            continue

        if not studio_code:
            issue = {
                'issue_code': 'invalid_studio_code',
                'message': f'Cannot derive studio_code from studio name: {studio_name}',
                'raw_value': studio_name,
                'row_index': idx,
            }
            issues.append(issue)
            logger.warning('sync_issue: %s', issue)
            continue

        if not period_code:
            issue = {
                'issue_code': 'invalid_period',
                'message': f'Cannot parse period: {period_raw}',
                'raw_value': period_raw,
                'row_index': idx,
                'studio_code': studio_code,
                'studio_name': studio_name,
            }
            issues.append(issue)
            logger.warning('sync_issue: %s', issue)
            continue

        base = {
            'studio_code': studio_code,
            'studio_name': studio_name,
            'period_code': period_code,
            'period_type': period_type,
            'event_time': event_time,
            'row_index': idx,
            'has_event_time': parsed_ts is not None,
        }

        for metric_idx, _, metric_code in metric_indices:
            raw_value = _normalize_token(_cell(row, metric_idx))
            normalized_rows.append({
                **base,
                'metric_code': metric_code,
                'raw_value': raw_value,
                'value_type_hint': 'int' if metric_code in INT_METRICS else 'decimal',
            })

        _capture_unknown_columns(normalized_headers, metric_indices, issues, idx)

    return {'rows': normalized_rows, 'issues': issues}


def _capture_unknown_columns(headers: list[str], metric_indices: list[tuple[int, str, str]], issues: list[dict], row_index: int) -> None:
    metric_header_set = {header_ru for _, header_ru, _ in metric_indices}
    allowed = metric_header_set | EMAIL_HEADERS | TIMESTAMP_HEADERS | {STUDIO_HEADER, PERIOD_HEADER}
    for header in headers:
        if not header:
            continue
        if header not in allowed:
            issues.append({
                'issue_code': 'unknown_column',
                'message': f'Column is not mapped: {header}',
                'raw_value': header,
                'row_index': row_index,
            })


def _find_header_index_any(headers: list[str], targets: list[str]) -> int | None:
    for target in targets:
        idx = _find_header_index(headers, target)
        if idx is not None:
            return idx
    return None


def _find_header_index(headers: list[str], target: str) -> int | None:
    normalized_target = _normalize_token(target)
    for i, header in enumerate(headers):
        if header == normalized_target:
            return i
    return None


def _find_first_header_index(headers: list[str], candidates: set[str]) -> int | None:
    for candidate in candidates:
        idx = _find_header_index(headers, candidate)
        if idx is not None:
            return idx
    return None


def _cell(row: list[str], idx: int | None) -> str:
    if idx is None or idx >= len(row):
        return ''
    return row[idx]


def _normalize_token(value: str | None) -> str:
    text = (value or '').replace('\ufeff', '').replace('\xa0', ' ').strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def _parse_ts(ts_raw: str) -> datetime | None:
    if not ts_raw:
        return None

    candidates = [
        lambda s: datetime.fromisoformat(s.replace('Z', '+00:00')),
        lambda s: datetime.strptime(s, '%d.%m.%Y %H:%M:%S').replace(tzinfo=timezone.utc),
        lambda s: datetime.strptime(s, '%m/%d/%Y %H:%M:%S').replace(tzinfo=timezone.utc),
    ]
    for parser in candidates:
        try:
            parsed = parser(ts_raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return None
