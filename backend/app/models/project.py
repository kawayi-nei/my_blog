from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Identity,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','published')", name="ck_projects_status"
        ),
        CheckConstraint(
            "slug ~ '^[a-z0-9-]+$'", name="ck_projects_slug_format"
        ),
        Index(
            "ix_projects_public_order",
            "status",
            text("featured DESC"),
            "sort_order",
            text("started_on DESC NULLS LAST"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    title_zh: Mapped[str] = mapped_column(String(200), nullable=False)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    summary_zh: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=text("''")
    )
    summary_en: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=text("''")
    )
    content_md_zh: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=text("''")
    )
    content_md_en: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=text("''")
    )
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tech_stack: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    demo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ended_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    featured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="draft", server_default="draft"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
