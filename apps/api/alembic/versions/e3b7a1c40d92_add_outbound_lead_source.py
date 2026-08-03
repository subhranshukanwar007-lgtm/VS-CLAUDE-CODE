"""add OUTBOUND lead source

Revision ID: e3b7a1c40d92
Revises: c71e4f0a92d8
Create Date: 2026-08-03 11:02:41.336712

Leads we sourced ourselves (an Apollo search, a list, a cold approach) need to be
separable from leads who came to us. Goal performance measures leads *per post*;
outbound leads never came from a post, and filing them under OTHER would inflate
the unattributed-lead count, which is the number that tells the user their
attribution is broken.

Label is UPPERCASE because SQLAlchemy persists the enum member *name*. See
tests/test_migrations.py — getting this wrong shipped a production-only bug once.

Postgres cannot drop a single enum label, so downgrade is a no-op rather than a
lie. Any row still on OUTBOUND would have nowhere to go.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e3b7a1c40d92'
down_revision: Union[str, None] = 'c71e4f0a92d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE lead_source ADD VALUE IF NOT EXISTS 'OUTBOUND'")


def downgrade() -> None:
    # Postgres has no DROP VALUE. Leaving the label in place is harmless; the
    # ORM simply stops writing it.
    pass
