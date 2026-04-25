from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    organization_name: str | None = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    organization_id: str | None

    model_config = {"from_attributes": True}


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_days: int | None = Field(default=None, ge=1, le=365)


class APIKeyOut(BaseModel):
    id: str
    name: str
    key: str  # shown only on creation
    created_at: str

    model_config = {"from_attributes": True}
