from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session


def run_sql_migrations(db: Session) -> None:
    migrations_dir = Path(__file__).resolve().parents[2] / 'migrations' / 'sql'
    for sql_file in sorted(migrations_dir.glob('*.sql')):
        sql_text = sql_file.read_text(encoding='utf-8')
        db.execute(text(sql_text))
    db.commit()
