"""A bank of content ideas, each one a problem someone actually has.

Why a bank rather than asking AI for a fresh topic each morning: an AI asked
"give me a fitness video idea" drifts toward the generic ("5 tips for a healthy
lifestyle") because that's the centre of gravity of everything written about
fitness. A curated list of specific, lived problems — *the back pain from sitting
nine hours at a desk*, not *back pain* — keeps the specificity that makes someone
stop scrolling, and lets the creator add the problems their own audience keeps
describing in the comments.

Ideas rotate by least-recently-used so the same topic doesn't resurface while
fresher ones sit unused, and today's pick is stable across a day so refreshing
the page doesn't reshuffle the plan.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.post import PostFormat, PostGoal


class IdeaSource(StrEnum):
    SEED = "seed"
    CUSTOM = "custom"


class ContentIdea(BaseModel):
    __tablename__ = "content_ideas"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    problem: Mapped[str] = mapped_column(
        Text, nullable=False, comment="The lived problem, stated specifically enough that someone recognises themselves"
    )
    angle: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="The surprising turn — what they believe vs what's actually going on"
    )
    suggested_goal: Mapped[PostGoal] = mapped_column(
        Enum(PostGoal, name="post_goal"), default=PostGoal.REACH, nullable=False
    )
    suggested_format: Mapped[PostFormat] = mapped_column(
        Enum(PostFormat, name="post_format"), default=PostFormat.REEL, nullable=False
    )
    source: Mapped[IdeaSource] = mapped_column(
        Enum(IdeaSource, name="idea_source"), default=IdeaSource.CUSTOM, nullable=False
    )

    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# Seeded on first use. Each is a situation someone lived through this week, not a
# topic: "back pain" is a category, "the back pain from sitting nine hours at a
# desk" is a Tuesday. The second one stops the scroll.
SEED_IDEAS: list[dict] = [
    {
        "problem": "Lower back pain from sitting at a desk for nine hours",
        "angle": "They stretch their back. The actual problem is tight hips taking no load.",
        "suggested_goal": PostGoal.REACH,
    },
    {
        "problem": "Slept eight hours and still woke up exhausted",
        "angle": "They blame sleep quantity. It's usually what they ate late, or no daylight in the morning.",
        "suggested_goal": PostGoal.REACH,
    },
    {
        "problem": "Eats healthy but the belly does not go",
        "angle": "Healthy food still has calories. Ghee, nuts and juices are where it hides.",
        "suggested_goal": PostGoal.REACH,
    },
    {
        "problem": "Six months in the gym, no visible change",
        "angle": "Same weight every session. Without progressive overload the body has no reason to change.",
        "suggested_goal": PostGoal.TRUST,
    },
    {
        "problem": "Feels bloated and heavy after every single meal",
        "angle": "Eating too fast and too little fibre — not a food allergy, which is where everyone jumps.",
        "suggested_goal": PostGoal.SAVES,
    },
    {
        "problem": "The weekend undoes the whole week of dieting",
        "angle": "Two days of surplus can erase five days of deficit. The maths, not the willpower.",
        "suggested_goal": PostGoal.SALES,
    },
    {
        "problem": "No time to cook, eats from the office canteen every day",
        "angle": "One 20-minute Sunday prep beats five perfect weekday meals that never happen.",
        "suggested_goal": PostGoal.SAVES,
    },
    {
        "problem": "Knees hurt going up stairs",
        "angle": "Usually weak glutes rather than bad knees. The knee is where it hurts, not where it starts.",
        "suggested_goal": PostGoal.REACH,
    },
    {
        "problem": "Eats well all day then raids the kitchen at 11pm",
        "angle": "Under-eating at breakfast and lunch is what builds the night craving.",
        "suggested_goal": PostGoal.TRUST,
    },
    {
        "problem": "Hair fall and constant weakness despite a full diet",
        "angle": "Full plate, low protein. Say to get tested — never diagnose.",
        "suggested_goal": PostGoal.TRUST,
    },
    {
        "problem": "Family thinks protein powder is a steroid",
        "angle": "Protein powder is food, not a drug. The conversation everyone in this audience has had.",
        "suggested_goal": PostGoal.TRUST,
    },
    {
        "problem": "Walks 10,000 steps daily and still gains weight",
        "angle": "Steps are not a licence. Movement is small next to what's on the plate.",
        "suggested_goal": PostGoal.REACH,
    },
    {
        "problem": "Started strong in January, quit by February",
        "angle": "The plan was built for someone with more time than they have.",
        "suggested_goal": PostGoal.TRUST,
    },
    {
        "problem": "Skips breakfast, then eats everything at lunch",
        "angle": "Fasting is fine. Fasting badly is what makes the afternoon a write-off.",
        "suggested_goal": PostGoal.SAVES,
    },
]
