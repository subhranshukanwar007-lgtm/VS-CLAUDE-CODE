"""Read/write access to a user's AutomationSetting row.

Rows are created lazily on first access so users who registered before this
feature existed don't need a data backfill, and so the defaults live in one place
(the model's column defaults) rather than being duplicated across callers.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.automation_setting import AutomationSetting
from app.models.post import Platform


def get_or_create(db: Session, owner_id: uuid.UUID) -> AutomationSetting:
    existing = db.scalar(select(AutomationSetting).where(AutomationSetting.owner_id == owner_id))
    if existing:
        return existing

    setting = AutomationSetting(owner_id=owner_id, auto_publish={})
    db.add(setting)
    try:
        db.commit()
    except IntegrityError:
        # Concurrent request created it first (owner_id is unique). Reuse theirs.
        db.rollback()
        setting = db.scalar(select(AutomationSetting).where(AutomationSetting.owner_id == owner_id))
        if setting is None:  # pragma: no cover - only if the row vanished mid-flight
            raise
        return setting

    db.refresh(setting)
    return setting


def is_auto_publish_enabled(db: Session, owner_id: uuid.UUID, platform: Platform) -> bool:
    """Defaults to False: a platform the user has never configured requires
    approval. Silence means "ask me", never "post it"."""

    setting = get_or_create(db, owner_id)
    return bool((setting.auto_publish or {}).get(platform.value, False))


def dm_trigger_keywords(setting: AutomationSetting) -> list[str]:
    if not setting.dm_trigger_keywords:
        return []
    return [kw.strip().lower() for kw in setting.dm_trigger_keywords.split(",") if kw.strip()]


def threads_keywords(setting: AutomationSetting) -> list[str]:
    if not setting.threads_keywords:
        return []
    return [kw.strip() for kw in setting.threads_keywords.split(",") if kw.strip()]
