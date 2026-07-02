"""Pydantic model for proxy request validation."""

from pydantic import BaseModel, Field, HttpUrl


class ProxyRequest(BaseModel):
    url: HttpUrl
    method: str = Field(default="GET", pattern=r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
