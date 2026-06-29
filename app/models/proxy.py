"""Pydantic model for proxy request validation."""

from pydantic import BaseModel, Field


class ProxyRequest(BaseModel):
    url: str
    method: str = Field(default="GET")
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
