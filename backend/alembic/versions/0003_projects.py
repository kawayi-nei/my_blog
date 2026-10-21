"""add projects table

Revision ID: 0003_projects
Revises: 0002_media
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_projects"
down_revision = "0002_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("title_zh", sa.String(200), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column(
            "summary_zh",
            sa.String(500),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "summary_en",
            sa.String(500),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "content_md_zh",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "content_md_en",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column(
            "tech_stack",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("repo_url", sa.String(500), nullable=True),
        sa.Column("demo_url", sa.String(500), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("ended_on", sa.Date(), nullable=True),
        sa.Column(
            "featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft','published')", name="ck_projects_status"
        ),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9-]+$'", name="ck_projects_slug_format"
        ),
    )
    op.execute(
        "CREATE INDEX ix_projects_public_order ON projects "
        "(status, featured DESC, sort_order ASC, started_on DESC NULLS LAST)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_projects_public_order")
    op.drop_table("projects")
