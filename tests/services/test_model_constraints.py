from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import pytest_asyncio

from backend.app.models.base import Base
from backend.app.models.gift import ActivityOffer, Gift, GiftBundleComponent, ProductOffer
from backend.app.models.taxonomy import GiftTypeDefinition


@pytest_asyncio.fixture
async def db_session():
    """Use SQLite with foreign keys enabled to exercise declared constraints."""
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
async def test_bundle_component_rejects_self_reference(db_session):
    """Catches a bundle that directly includes itself."""
    gift = Gift(canonical_name="周末礼物包", gift_type_code="product", is_bundle=True)
    db_session.add(gift)
    await db_session.flush()
    db_session.add(GiftBundleComponent(bundle_gift_id=gift.id, component_gift_id=gift.id))

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_offer_ranges_reject_negative_or_reversed_values(db_session):
    """Catches invalid product and activity offer monetary range persistence."""
    product = Gift(canonical_name="商品渠道", gift_type_code="product")
    activity = Gift(canonical_name="活动渠道", gift_type_code="activity")
    db_session.add_all([product, activity])
    await db_session.flush()
    db_session.add_all(
        [
            ProductOffer(gift_id=product.id, merchant="店铺", current_price=Decimal("-1.00")),
            ActivityOffer(
                gift_id=activity.id, provider_name="工作室",
                current_price_min=Decimal("80.00"), current_price_max=Decimal("40.00"),
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()
