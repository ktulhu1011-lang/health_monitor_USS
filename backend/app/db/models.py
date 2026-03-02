import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Studio(Base):
    __tablename__ = 'studios'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    studio_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Period(Base):
    __tablename__ = 'periods'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    period_type: Mapped[str] = mapped_column(String, nullable=False, default='quarter')
    start_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)


class Metric(Base):
    __tablename__ = 'metrics'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    group_code: Mapped[str] = mapped_column(String, nullable=False, default='other')
    value_type: Mapped[str] = mapped_column(String, nullable=False, default='decimal')
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class FactValue(Base):
    __tablename__ = 'fact_values'
    __table_args__ = (UniqueConstraint('studio_id', 'period_id', 'metric_id', name='uq_fact_values_key'),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    studio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('studios.id'), nullable=False)
    period_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('periods.id'), nullable=False)
    metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('metrics.id'), nullable=False)
    value_decimal: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    value_int: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default='google_sheet')
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DataQualityIssue(Base):
    __tablename__ = 'data_quality_issues'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    studio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('studios.id'), nullable=True)
    period_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('periods.id'), nullable=True)
    metric_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('metrics.id'), nullable=True)
    severity: Mapped[str] = mapped_column(String, nullable=False, default='error')
    issue_code: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source: Mapped[str] = mapped_column(String, nullable=False, default='google_sheet')


class SyncState(Base):
    __tablename__ = 'sync_state'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
