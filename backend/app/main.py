from fastapi import FastAPI

from app.api.v1.routes import router
from app.db.database import SessionLocal
from app.services.migrations import run_sql_migrations

app = FastAPI(title='Health Monitor USS', version='1.0.0')
app.include_router(router)


@app.on_event('startup')
def startup() -> None:
    db = SessionLocal()
    try:
        run_sql_migrations(db)
    finally:
        db.close()
