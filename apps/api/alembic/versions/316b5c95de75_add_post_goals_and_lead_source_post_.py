"""add post goals and lead source post attribution

Revision ID: 316b5c95de75
Revises: a9e9c011db54
Create Date: 2026-07-30 10:00:00.994151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '316b5c95de75'
down_revision: Union[str, None] = 'a9e9c011db54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leads', sa.Column('source_post_id', sa.UUID(), nullable=True, comment="The post this lead engaged with, when engagement capture could match the webhook's media id to a published post. ON DELETE SET NULL: deleting a post must not delete the leads it earned."))
    op.create_index(op.f('ix_leads_source_post_id'), 'leads', ['source_post_id'], unique=False)
    op.create_foreign_key(
        'fk_leads_source_post_id_posts', 'leads', 'posts', ['source_post_id'], ['id'], ondelete='SET NULL'
    )

    # Create the enum type explicitly: add_column does not create it reliably, and
    # server_default is required because the column is NOT NULL and existing rows
    # need a value. Labels are the Python enum's *names* (uppercase) because that
    # is what SQLAlchemy persists - see tests/test_migrations.py.
    post_goal = sa.Enum('REACH', 'LEADS', 'SALES', 'TRUST', 'SAVES', name='post_goal')
    post_goal.create(op.get_bind(), checkfirst=True)
    op.add_column('posts', sa.Column('goal', post_goal, nullable=False, server_default='REACH'))
    op.alter_column('posts', 'external_post_id',
               existing_type=sa.VARCHAR(length=255),
               comment="The platform's own id for the published post. Indexed because engagement capture looks leads up by it.",
               existing_nullable=True)
    op.create_index(op.f('ix_posts_external_post_id'), 'posts', ['external_post_id'], unique=False)
    op.create_index(op.f('ix_posts_goal'), 'posts', ['goal'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index(op.f('ix_posts_goal'), table_name='posts')
    op.drop_index(op.f('ix_posts_external_post_id'), table_name='posts')
    op.alter_column('posts', 'external_post_id',
               existing_type=sa.VARCHAR(length=255),
               comment=None,
               existing_comment="The platform's own id for the published post. Indexed because engagement capture looks leads up by it.",
               existing_nullable=True)
    op.drop_column('posts', 'goal')
    op.execute('DROP TYPE IF EXISTS post_goal')
    op.drop_constraint('fk_leads_source_post_id_posts', 'leads', type_='foreignkey')
    op.drop_index(op.f('ix_leads_source_post_id'), table_name='leads')
    op.drop_column('leads', 'source_post_id')
