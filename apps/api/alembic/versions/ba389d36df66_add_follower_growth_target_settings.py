"""add follower growth target settings

Revision ID: ba389d36df66
Revises: 316b5c95de75
Create Date: 2026-07-30 10:29:33.058586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ba389d36df66'
down_revision: Union[str, None] = '316b5c95de75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('automation_settings', sa.Column('follower_goal', sa.Integer(), nullable=True, comment='Target follower count, e.g. 100000. Null means no goal set.'))
    op.add_column('automation_settings', sa.Column('goal_deadline', sa.Date(), nullable=True, comment='Date the follower goal should be reached by'))
    op.add_column('automation_settings', sa.Column('reels_per_week_target', sa.Integer(), nullable=False, server_default='5', comment='Reels specifically, not posts. Reels are the only format Instagram pushes to non-followers, so follower growth is a reel target.'))


def downgrade() -> None:
    op.drop_column('automation_settings', 'reels_per_week_target')
    op.drop_column('automation_settings', 'goal_deadline')
    op.drop_column('automation_settings', 'follower_goal')
