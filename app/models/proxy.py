"""Pydantic model for proxy request validation."""

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ProxyRequest(BaseModel):
    url: HttpUrl
    method: str = Field(default="GET", pattern=r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None

    @field_validator("url")
    @classmethod
    def validate_port(cls, v: HttpUrl) -> HttpUrl:
        # Only allow default ports 80/443 (explicit non-standard ports rejected).
        # v.port returns scheme default when unspecified, so only explicit odd ports fail.
        port = v.port
        if port is not None and port not in (80, 443):
            msg = f"Only ports 80/443 allowed, got {port}"
            raise ValueError(msg)
        return v


class ProxyResponse(BaseModel):
    status: str = Field(..., description="Proxy execution status")
    status_code: int = Field(..., description="HTTP status code from upstream server")
    time_ms: int = Field(..., description="Elapsed time in milliseconds")
    size_bytes: int = Field(..., description="Response size in bytes")
    headers: dict[str, str] = Field(default_factory=dict, description="Response headers")
    body: str = Field(..., description="Response body text")
