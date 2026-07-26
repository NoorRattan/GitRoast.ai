import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.services.scoring_constants import SCHEMA_VERSION


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(39), index=True, nullable=False)
    profile_strength: Mapped[int] = mapped_column(Integer, nullable=False)
    project_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    commit_consistency: Mapped[int] = mapped_column(Integer, nullable=False)
    tech_diversity: Mapped[int] = mapped_column(Integer, nullable=False)
    percentile_benchmark: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=SCHEMA_VERSION)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    review_items: Mapped[list["ReviewQueueItem"]] = relationship(back_populates="audit")


class OptedOutUsername(Base):
    __tablename__ = "opted_out_usernames"

    username: Mapped[str] = mapped_column(String(39), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReviewQueueItem(Base):
    __tablename__ = "review_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    generated_content: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        default=ReviewStatus.pending,
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    audit: Mapped[Audit] = relationship(back_populates="review_items")
