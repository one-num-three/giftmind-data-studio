from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from backend.app.models.base import CURRENT_SCHEMA_VERSION, Base
from backend.app.models.custom_fields import CustomFieldDefinition, GiftCustomFieldValue
from backend.app.models.gift import (
    ActivityDetail,
    ActivityOffer,
    Gift,
    GiftBundleComponent,
    ProductDetail,
    ProductOffer,
)
from backend.app.models.taxonomy import GiftTypeDefinition


@pytest_asyncio.fixture
async def db_session():
    """Run every schema contract test against a real foreign-key SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.execute(text("PRAGMA foreign_keys=ON"))
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            GiftTypeDefinition.__table__.insert(),
            [
                {"code": "product", "name": "商品", "status": "active", "contract_version": 1},
                {"code": "activity", "name": "活动", "status": "active", "contract_version": 1},
            ],
        )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_product_and_activity_details_are_separate(db_session):
    """Catches a regression that merges type-specific fields into shared gifts."""
    product = Gift(canonical_name="黄铜书签", gift_type_code="product")
    activity = Gift(canonical_name="陶艺双人课", gift_type_code="activity")
    db_session.add_all([product, activity])
    await db_session.flush()
    db_session.add(ProductDetail(gift_id=product.id, product_form="physical"))
    db_session.add(ActivityDetail(gift_id=activity.id, activity_mode="offline"))
    await db_session.commit()

    product_detail = await db_session.get(ProductDetail, product.id)
    activity_detail = await db_session.get(ActivityDetail, activity.id)

    assert product_detail.product_form == "physical"
    assert activity_detail.activity_mode == "offline"


@pytest.mark.asyncio
async def test_gift_type_must_reference_a_defined_type(db_session):
    """Catches loss of the text foreign key that limits top-level types."""
    db_session.add(Gift(canonical_name="未知类型礼物", gift_type_code="unknown"))

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_price_and_lead_ranges_reject_invalid_bounds(db_session):
    """Catches removal of the shared non-negative and min/max database checks."""
    db_session.add(
        Gift(
            canonical_name="无效范围", gift_type_code="product",
            price_min=Decimal("20.00"), price_max=Decimal("10.00"),
            lead_days_min=4, lead_days_max=2,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_custom_field_value_makes_machine_key_immutable(db_session):
    """Catches a machine-key rename after collected values exist."""
    gift = Gift(canonical_name="可扩展礼物", gift_type_code="product")
    field = CustomFieldDefinition(
        machine_key="finish_style", display_name="表面风格", scope="product",
        value_type="single_choice", state="active", introduced_version=1,
    )
    db_session.add_all([gift, field])
    await db_session.flush()
    db_session.add(GiftCustomFieldValue(gift_id=gift.id, field_definition_id=field.id, value_json="\"matte\""))
    await db_session.commit()

    field.machine_key = "surface_style"
    with pytest.raises(IntegrityError):
        await db_session.commit()


def test_schema_version_is_initial_contract_version():
    """Catches accidental drift between code and the initial migration contract."""
    assert CURRENT_SCHEMA_VERSION == 1


def test_initial_migration_creates_versioned_contract_and_seed_types(tmp_path):
    """Catches a migration that omits a persisted contract table or initial types."""
    database_path = tmp_path / "initial.sqlite3"
    repository_root = Path(__file__).parents[2]
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        assert {
            "gifts", "product_details", "product_offers", "activity_details", "activity_offers",
            "gift_bundle_components", "gift_type_definitions", "dimension_options",
            "custom_field_definitions", "gift_custom_field_values", "gift_images", "audit_events",
            "ai_runs", "ai_threads", "ai_messages", "ai_suggestion_runs",
            "import_runs", "backup_records",
        }.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
            seeded_codes = connection.execute(
                select(GiftTypeDefinition.code).order_by(GiftTypeDefinition.code)
            ).scalars().all()
            assert revision == "0003_h5_shares"
        assert seeded_codes == ["activity", "product"]
    finally:
        engine.dispose()


@pytest.fixture
def migrated_engine(tmp_path):
    """Return a clean Alembic-upgraded SQLite engine with FK enforcement enabled."""
    database_path = tmp_path / "migrated.sqlite3"
    repository_root = Path(__file__).parents[2]
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    try:
        yield engine
    finally:
        engine.dispose()


def test_migration_allows_only_product_and_activity_to_be_active(migrated_engine):
    """Catches a future top-level type becoming active before its formal migration."""
    with Session(migrated_engine) as session:
        session.add(
            GiftTypeDefinition(code="future", name="未来类型", status="draft", contract_version=2)
        )
        session.commit()

        session.add(
            GiftTypeDefinition(code="future_active", name="未来激活类型", status="active", contract_version=2)
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        future_type = session.get(GiftTypeDefinition, "future")
        future_type.status = "active"
        with pytest.raises(IntegrityError):
            session.commit()


def test_migration_rejects_gift_for_inactive_type_definition(migrated_engine):
    """Catches gifts that reference a defined but not yet active future type."""
    with Session(migrated_engine) as session:
        session.add(
            GiftTypeDefinition(code="future", name="未来类型", status="draft", contract_version=2)
        )
        session.commit()
        session.add(Gift(canonical_name="未来礼物", gift_type_code="future"))

        with pytest.raises(IntegrityError):
            session.commit()


def test_migration_rejects_wrong_type_details_offers_and_mixed_details(migrated_engine):
    """Catches product/activity detail or offer rows attached to the wrong gift type."""
    with Session(migrated_engine) as session:
        product = Gift(canonical_name="迁移商品", gift_type_code="product")
        activity = Gift(canonical_name="迁移活动", gift_type_code="activity")
        session.add_all([product, activity])
        session.commit()

        session.add(ActivityDetail(gift_id=product.id, activity_mode="offline"))
        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
        session.add(
            Gift(
                canonical_name="迁移无效价格", gift_type_code="product",
                price_min=Decimal("20.00"), price_max=Decimal("10.00"),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            GiftBundleComponent(bundle_gift_id=product.id, component_gift_id="missing-gift")
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(ProductDetail(gift_id=activity.id, product_form="physical"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(ProductOffer(gift_id=activity.id, merchant="错误渠道"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(ActivityOffer(gift_id=product.id, provider_name="错误活动渠道"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(ProductDetail(gift_id=product.id, product_form="physical"))
        session.commit()
        session.add(ActivityDetail(gift_id=product.id, activity_mode="offline"))
        with pytest.raises(IntegrityError):
            session.commit()
