"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "posts",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "excerpt",
            sa.String(500),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("language", sa.String(5), nullable=False, server_default="zh"),
        sa.Column("status", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
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
        sa.CheckConstraint("language IN ('zh','en')", name="ck_posts_language"),
        sa.CheckConstraint(
            "status IN ('draft','published')", name="ck_posts_status"
        ),
        sa.CheckConstraint("slug ~ '^[a-z0-9-]+$'", name="ck_posts_slug_format"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
    )
    op.create_table(
        "post_tags",
        sa.Column(
            "post_id",
            sa.BigInteger(),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_posts_status_published_at", "posts", ["status", "published_at"]
    )
    op.execute(
        "CREATE INDEX ix_posts_title_trgm ON posts USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_posts_excerpt_trgm ON posts USING gin (excerpt gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_posts_content_trgm ON posts USING gin (content_md gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_posts_content_trgm")
    op.execute("DROP INDEX IF EXISTS ix_posts_excerpt_trgm")
    op.execute("DROP INDEX IF EXISTS ix_posts_title_trgm")
    op.drop_index("ix_posts_status_published_at", table_name="posts")
    op.drop_table("post_tags")
    op.drop_table("tags")
    op.drop_table("posts")
    op.drop_table("users")
