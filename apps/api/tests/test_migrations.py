"""Guards that the migration chain produces the schema the ORM expects.

Why this file exists: conftest builds the test schema with
``Base.metadata.create_all()``, so the whole suite can pass while
``alembic upgrade head`` produces a *different*, broken schema. That actually
happened — three migrations added enum labels in lowercase while SQLAlchemy
persists enum names in uppercase, so follow-up notifications, video
notifications, follow-up AI generations and Higgsfield video generations all
raised ``invalid input value for enum`` in any migrated database, which means
every real deployment. Tests were green the whole time.

These tests run migrations against a scratch database and compare enum labels to
the Python enums, so a miscased or missing label fails here instead of in
production.
"""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

import app.config as config_module

from app.models.ai_generation import AIGenerationKind
from app.models.ai_generation import AIProvider as AIProviderKind
from app.models.automation_setting import ReplyLanguage
from app.models.lead import LeadIntent, LeadSource, LeadStatus
from app.models.notification import NotificationType
from app.models.post import Platform, PostFormat, PostGoal, PostStatus
from app.models.private_reply import PrivateReplyStatus
from app.models.question_opportunity import QuestionSource, QuestionStatus
from app.models.user import UserRole
from app.models.video_generation import VideoGenerationStatus
from app.models.video_generation import VideoProviderKind
from app.models.whatsapp import MessageDirection, MessageStatus

# Enum type name in Postgres -> the Python enum it must mirror.
ENUM_EXPECTATIONS = {
    "notification_type": NotificationType,
    "ai_generation_kind": AIGenerationKind,
    "ai_provider": AIProviderKind,
    "lead_source": LeadSource,
    "lead_status": LeadStatus,
    "lead_intent": LeadIntent,
    "post_platform": Platform,
    "post_format": PostFormat,
    "post_status": PostStatus,
    "post_goal": PostGoal,
    "private_reply_status": PrivateReplyStatus,
    "user_role": UserRole,
    "video_generation_status": VideoGenerationStatus,
    "video_provider": VideoProviderKind,
    "question_source": QuestionSource,
    "question_status": QuestionStatus,
    "reply_language": ReplyLanguage,
    "wa_direction": MessageDirection,
    "wa_message_status": MessageStatus,
}

MIGRATED_DB_NAME = "social_os_migrationcheck"


@pytest.fixture(scope="module")
def migrated_engine():
    """A scratch database built purely by `alembic upgrade head`."""

    base_url = make_url(os.environ["DATABASE_URL"])
    admin_url = base_url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{MIGRATED_DB_NAME}"'))
        conn.execute(text(f'CREATE DATABASE "{MIGRATED_DB_NAME}"'))
    admin_engine.dispose()

    target_url = base_url.set(database=MIGRATED_DB_NAME)
    rendered = target_url.render_as_string(hide_password=False)

    # alembic/env.py sets sqlalchemy.url from app settings unconditionally, so
    # pointing the migrations at the scratch database means overriding settings
    # for the duration of the upgrade.
    original_database_url = config_module.settings.database_url
    config_module.settings.database_url = rendered
    try:
        alembic_config = Config(str(_alembic_ini()))
        alembic_config.set_main_option("sqlalchemy.url", rendered)
        command.upgrade(alembic_config, "head")
    finally:
        config_module.settings.database_url = original_database_url

    engine = create_engine(target_url, future=True)
    yield engine
    engine.dispose()

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{MIGRATED_DB_NAME}"'))
    admin_engine.dispose()


def _alembic_ini():
    from pathlib import Path

    return Path(__file__).resolve().parent.parent / "alembic.ini"


def _labels(engine, enum_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = :name"
            ),
            {"name": enum_name},
        ).all()
    return {row[0] for row in rows}


@pytest.mark.parametrize("enum_name", sorted(ENUM_EXPECTATIONS))
def test_migrated_enum_labels_match_python_enum(migrated_engine, enum_name):
    """SQLAlchemy persists enum *names*, so every Python member name must exist as
    a label in the migrated database — otherwise writing that value raises
    `invalid input value for enum` at runtime."""

    python_enum = ENUM_EXPECTATIONS[enum_name]
    expected = {member.name for member in python_enum}
    actual = _labels(migrated_engine, enum_name)

    assert actual, f"enum type {enum_name!r} does not exist in the migrated database"
    missing = expected - actual
    assert not missing, (
        f"{enum_name} is missing label(s) {sorted(missing)} that the ORM will try to "
        f"write. Add them in a migration with the exact uppercase member name."
    )


def test_no_lowercase_duplicate_labels(migrated_engine):
    """Catches the specific mistake that caused this file to exist: a migration
    adding a label using the enum's *value* alongside its correctly-cased name."""

    offenders: list[str] = []
    for enum_name, python_enum in ENUM_EXPECTATIONS.items():
        actual = _labels(migrated_engine, enum_name)
        valid_names = {member.name for member in python_enum}
        for label in actual - valid_names:
            if label.upper() in valid_names:
                offenders.append(f"{enum_name}.{label} (should be {label.upper()})")
    assert not offenders, f"miscased enum labels left in the schema: {offenders}"
