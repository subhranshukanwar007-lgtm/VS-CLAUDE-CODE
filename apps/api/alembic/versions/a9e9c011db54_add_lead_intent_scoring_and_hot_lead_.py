"""add lead intent scoring and hot lead notifications

Also repairs four enum labels that earlier migrations added in the wrong case.

SQLAlchemy's Enum type persists a Python enum's *name* (``FOLLOW_UP_SUGGESTED``),
not its value (``follow_up_suggested``). Three earlier migrations hand-wrote
``ADD VALUE`` with the lowercase value, so any database built by
``alembic upgrade head`` — i.e. every real deployment — had labels the ORM could
never write. Creating a follow-up notification, a video-ready/failed
notification, a follow-up AI generation, or any Higgsfield video generation
failed with ``invalid input value for enum``.

The test suite did not catch this because conftest builds its schema with
``Base.metadata.create_all()`` rather than by running migrations, so tests only
ever saw correctly-cased labels.

Postgres cannot drop an enum label, but it can rename one in place (PG 10+),
which also carries any existing rows over.

Revision ID: a9e9c011db54
Revises: 4023d6db3f6c
Create Date: 2026-07-30 04:52:11.104882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a9e9c011db54'
down_revision: Union[str, None] = '4023d6db3f6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (enum type, wrong label, correct label)
_MISCASED_LABELS = (
    ("notification_type", "follow_up_suggested", "FOLLOW_UP_SUGGESTED"),
    ("notification_type", "video_ready", "VIDEO_READY"),
    ("notification_type", "video_failed", "VIDEO_FAILED"),
    ("ai_generation_kind", "follow_up", "FOLLOW_UP"),
    ("video_provider", "higgsfield", "HIGGSFIELD"),
)


def _rename_label(enum_name: str, old: str, new: str) -> None:
    """Rename `old` to `new` only if `old` exists and `new` doesn't — so this is a
    no-op on a database that already has correct labels (one built by
    create_all, or one already upgraded)."""

    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = '{enum_name}' AND e.enumlabel = '{old}'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = '{enum_name}' AND e.enumlabel = '{new}'
            ) THEN
                ALTER TYPE {enum_name} RENAME VALUE '{old}' TO '{new}';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for enum_name, wrong, correct in _MISCASED_LABELS:
        _rename_label(enum_name, wrong, correct)

    # New notification type for the hot-lead alert. Alembic's autogenerate never
    # detects added enum values, so this is written by hand — correctly cased.
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'HOT_LEAD'")

    lead_intent = sa.Enum('UNKNOWN', 'COLD', 'WARM', 'HOT', name='lead_intent')
    lead_intent.create(op.get_bind(), checkfirst=True)

    # server_default is required because the column is NOT NULL and existing rows
    # need a value. It stays on the column afterwards so plain SQL inserts also
    # get a sane default.
    op.add_column(
        'leads',
        sa.Column('intent', lead_intent, nullable=False, server_default='UNKNOWN'),
    )
    op.add_column(
        'leads',
        sa.Column(
            'intent_reason',
            sa.String(length=500),
            nullable=True,
            comment="The AI's one-line justification, shown to the user so the score is auditable",
        ),
    )
    op.add_column('leads', sa.Column('intent_scored_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_leads_intent'), 'leads', ['intent'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_leads_intent'), table_name='leads')
    op.drop_column('leads', 'intent_scored_at')
    op.drop_column('leads', 'intent_reason')
    op.drop_column('leads', 'intent')
    op.execute('DROP TYPE IF EXISTS lead_intent')

    # Deliberately not reverting the label renames: they were a bug, and putting
    # the miscased labels back would only re-break the ORM.
