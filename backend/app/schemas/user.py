from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    preferred_language: str
    timezone: str
    totp_confirmed: bool
    is_safety_officer: bool
    created_at: datetime
