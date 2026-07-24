from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    avatar_url: str | None = None
    brand_voice: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    brand_voice: str | None = None


class UserRoleUpdate(BaseModel):
    role: UserRole
