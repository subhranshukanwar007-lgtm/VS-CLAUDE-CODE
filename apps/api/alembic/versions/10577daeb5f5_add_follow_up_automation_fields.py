"""add follow-up automation fields

Revision ID: 10577daeb5f5
Revises: 0508bca26a5c
Create Date: 2026-07-27 04:39:54.567265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '10577daeb5f5'
down_revision: Union[str, None] = '0508bca26a5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE ai_generation_kind ADD VALUE IF NOT EXISTS 'follow_up'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'follow_up_suggested'")
    op.add_column('leads', sa.Column('last_follow_up_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'users', sa.Column('follow_up_days', sa.Integer(), nullable=False, server_default='5')
    )
    op.alter_column('users', 'follow_up_days', server_default=None)


def downgrade() -> None:
    op.drop_column('users', 'follow_up_days')
    op.drop_column('leads', 'last_follow_up_at')
    # Postgres does not support removing a value from an enum type; the added
    # enum labels ('follow_up', 'follow_up_suggested') intentionally remain.
