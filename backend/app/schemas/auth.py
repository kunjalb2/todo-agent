"""Authentication schemas."""
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    exp: int


class UserCreate(BaseModel):
    """User registration schema."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class UserLogin(BaseModel):
    """User login schema."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserUpdate(BaseModel):
    """User profile update schema."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class ChangePassword(BaseModel):
    """Change password schema."""

    current_password: str = Field(min_length=1, max_length=100)
    new_password: str = Field(min_length=6, max_length=100)


class UserResponse(BaseModel):
    """User response schema."""

    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True
