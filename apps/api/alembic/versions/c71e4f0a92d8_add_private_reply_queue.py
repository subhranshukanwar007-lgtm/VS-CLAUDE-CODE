"""add private reply (comment -> auto-DM) queue

Revision ID: c71e4f0a92d8
Revises: 244c2a451120
Create Date: 2026-08-03 09:12:04.118377

Enum labels are the Python member names in UPPERCASE, because SQLAlchemy
persists ``PrivateReplyStatus.PENDING`` as the string ``"PENDING"``, not as its
value ``"pending"``. Getting this wrong produced a class of production-only bug
once already (see tests/test_migrations.py) — every write raised
``invalid input value for enum`` in a migrated database while the test suite,
which builds its schema with ``create_all()``, stayed green.

``post_platform`` already exists from the posts migration, so it is referenced
with ``create_type=False``; letting alembic re-create a shared enum fails on a
second use with "type already exists".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c71e4f0a92d8'
down_revision: Union[str, None] = '244c2a451120'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'private_replies',
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('lead_id', sa.UUID(), nullable=True),
        sa.Column(
            'platform',
            postgresql.ENUM(
                'INSTAGRAM', 'FACEBOOK', 'THREADS', 'X', 'YOUTUBE', 'LINKEDIN',
                'TIKTOK', 'PINTEREST',
                name='post_platform',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('comment_id', sa.String(length=255), nullable=False),
        sa.Column('recipient_username', sa.String(length=255), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'SENT', 'FAILED', 'SKIPPED', name='private_reply_status'),
            nullable=False,
        ),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    # Unique, not merely indexed: this constraint is the deduplication that stops
    # a redelivered Meta webhook from DMing the same person twice.
    op.create_index(op.f('ix_private_replies_comment_id'), 'private_replies', ['comment_id'], unique=True)
    op.create_index(op.f('ix_private_replies_owner_id'), 'private_replies', ['owner_id'], unique=False)
    op.create_index(
        'ix_private_replies_status_created', 'private_replies', ['status', 'created_at'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_private_replies_status_created', table_name='private_replies')
    op.drop_index(op.f('ix_private_replies_owner_id'), table_name='private_replies')
    op.drop_index(op.f('ix_private_replies_comment_id'), table_name='private_replies')
    op.drop_table('private_replies')
    op.execute('DROP TYPE IF EXISTS private_reply_status')
