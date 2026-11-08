"""Add role to user table

Revision ID: 1c4f8e2a9b70
Revises: 826cb9b5988f
Create Date: 2026-11-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1c4f8e2a9b70"
down_revision = "826cb9b5988f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column(
            "role",
            sa.String(length=20),
            server_default="user",
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("user", "role")
