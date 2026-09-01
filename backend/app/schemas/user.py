from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from backend.app.models.user import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    created_at: datetime
