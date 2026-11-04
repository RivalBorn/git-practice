"""add recipe tags

Revision ID: 18891d38c51d
Revises: c9f34a4f78f5
Create Date: 2026-10-17 16:41:58.509073

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '18891d38c51d'
down_revision = 'c9f34a4f78f5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "recipe_tags",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("recipe_id", "tag_id"),
    )


def downgrade():
    op.drop_table("recipe_tags")
    op.drop_table("tags")
