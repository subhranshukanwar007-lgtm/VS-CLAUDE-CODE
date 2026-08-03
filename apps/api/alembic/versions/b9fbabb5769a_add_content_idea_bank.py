"""add content idea bank

Revision ID: b9fbabb5769a
Revises: ba389d36df66
Create Date: 2026-07-30 10:38:38.607066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b9fbabb5769a'
down_revision: Union[str, None] = 'ba389d36df66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('content_ideas',
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('problem', sa.Text(), nullable=False, comment='The lived problem, stated specifically enough that someone recognises themselves'),
    sa.Column('angle', sa.Text(), nullable=True, comment="The surprising turn — what they believe vs what's actually going on"),
    sa.Column('suggested_goal', postgresql.ENUM('REACH', 'LEADS', 'SALES', 'TRUST', 'SAVES', name='post_goal', create_type=False), nullable=False),
    sa.Column('suggested_format', postgresql.ENUM('REEL', 'POST', 'STORY', 'CAROUSEL', 'VIDEO', name='post_format', create_type=False), nullable=False),
    sa.Column('source', sa.Enum('SEED', 'CUSTOM', name='idea_source'), nullable=False),
    sa.Column('times_used', sa.Integer(), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_ideas_owner_id'), 'content_ideas', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_content_ideas_owner_id'), table_name='content_ideas')
    op.drop_table('content_ideas')
    # post_goal and post_format are shared with other tables; only idea_source is
    # owned by this migration.
    op.execute('DROP TYPE IF EXISTS idea_source')
