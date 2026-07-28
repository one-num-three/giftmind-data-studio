"""Image assets that belong to gifts."""

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GiftImage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "gift_images"

    gift_id: Mapped[str] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("width IS NULL OR width > 0", name="ck_gift_image_width"),
        CheckConstraint("height IS NULL OR height > 0", name="ck_gift_image_height"),
        CheckConstraint("file_size_bytes >= 0", name="ck_gift_image_size"),
        CheckConstraint("display_order >= 0", name="ck_gift_image_display_order"),
    )
