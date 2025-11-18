from pydantic import BaseModel


class AuthContext(BaseModel):
    user: str | None = None
    environment: str | None = None
    token: str | None = None
    permissions: list[str] = []
