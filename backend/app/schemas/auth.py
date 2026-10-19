from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    username: str


class MeResponse(BaseModel):
    username: str
