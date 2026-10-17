"""add prep_time_minutes to recipe

Revision ID: c9f34a4f78f5
Revises: 92140465ffd9
Create Date: 2026-10-15 23:55:44.977959

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9f34a4f78f5'
down_revision = '92140465ffd9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prep_time_minutes', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('recipes', schema=None) as batch_op:
        batch_op.drop_column('prep_time_minutes')
