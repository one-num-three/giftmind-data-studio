"""Alembic environment for GiftMind's versioned data contract."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.models import (  # noqa: F401 - importing registers all metadata tables.
    AIRun,
    ActivityDetail,
    ActivityOffer,
    AuditEvent,
    BackupRecord,
    CustomFieldDefinition,
    DimensionOption,
    Gift,
    GiftBundleComponent,
    GiftCustomFieldValue,
    GiftImage,
    GiftTypeDefinition,
    ImportRun,
    ProductDetail,
    ProductOffer,
)
from backend.app.models.base import Base


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """Adapt the async application URL to Alembic's synchronous engine."""
    return config.get_main_option("sqlalchemy.url").replace("+aiosqlite", "")


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=_database_url(),
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
