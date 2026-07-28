"""Auditable operational metadata without credentials or session revocation state."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class AuditEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "audit_events"

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), index=True)
    payload_json: Mapped[dict | list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AIRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ai_runs"

    gift_id: Mapped[str | None] = mapped_column(ForeignKey("gifts.id", ondelete="SET NULL"), index=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(128))
    summary_json: Mapped[dict | list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_ai_run_duration"),
        CheckConstraint("input_tokens IS NULL OR input_tokens >= 0", name="ck_ai_run_input_tokens"),
        CheckConstraint("output_tokens IS NULL OR output_tokens >= 0", name="ck_ai_run_output_tokens"),
    )


class ImportRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "import_runs"

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    import_format: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_report_json: Mapped[dict | list | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("total_records >= 0", name="ck_import_total_records"),
        CheckConstraint("imported_records >= 0", name="ck_import_imported_records"),
        CheckConstraint("rejected_records >= 0", name="ck_import_rejected_records"),
    )


class BackupRecord(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "backup_records"

    filename: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    backup_kind: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="complete", nullable=False)
    manifest_json: Mapped[dict | list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("file_size_bytes >= 0", name="ck_backup_file_size"),
        CheckConstraint("schema_version >= 1", name="ck_backup_schema_version"),
    )
