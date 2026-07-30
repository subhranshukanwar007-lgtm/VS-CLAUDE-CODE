from uuid import UUID

from pydantic import BaseModel, Field

from app.models.ai_generation import AIProvider as AIProviderKind
from app.models.automation_setting import ReplyLanguage
from app.models.post import Platform


class ScriptBeat(BaseModel):
    """One timed moment of the video.

    Kept as beats rather than one block of prose because each beat needs three
    *different* things produced for it — a spoken line for the avatar, an
    on-screen caption, and a shot instruction — and they have to stay aligned to
    the same second.
    """

    start_seconds: int
    end_seconds: int
    spoken: str = Field(description="What the avatar says out loud")
    caption: str = Field(description="On-screen text for this beat, in the user's chosen script")
    broll: str = Field(description="What to show on screen while this line is spoken")


class ContentPackage(BaseModel):
    topic: str
    platform: Platform
    language: ReplyLanguage
    duration_seconds: int

    hooks: list[str] = Field(description="Opening line options, strongest first")
    beats: list[ScriptBeat]
    higgsfield_prompt: str = Field(
        description=(
            "Ready to paste into Higgsfield alongside your own trained avatar and voice. "
            "Describes framing, motion and delivery only — it never describes a face, "
            "because the face comes from your avatar."
        )
    )
    broll_notes: str = Field(description="How to shoot or source the B-roll, overall")
    post_caption: str
    cta: str
    hashtags: str

    generation_id: UUID | None = None
    provider: AIProviderKind | None = None
    model: str | None = None


class ContentPackageRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    platform: Platform = Platform.INSTAGRAM
    duration_seconds: int = Field(default=30, ge=10, le=120)
    language: ReplyLanguage | None = Field(
        default=None, description="Defaults to your Settings reply language"
    )
    provider: AIProviderKind | None = None
