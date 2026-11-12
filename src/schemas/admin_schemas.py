from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: str


class SetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=10, max_length=72)


class AdminMe(BaseModel):
    id: int
    email: EmailStr
