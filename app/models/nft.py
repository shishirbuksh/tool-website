"""Pydantic models for NFT generation and fractal parameter validation."""

from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator


class NFTRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000, description="Text prompt for generation")
    style: Literal["3d", "cyberpunk", "pixel"] = Field(
        default="3d", description="Art style for generation"
    )
    provider: Literal["local", "openai", "gemini", "deepseek"] = Field(
        default="local", description="AI provider (local, openai, gemini, deepseek)"
    )
    api_key: SecretStr | None = Field(default=None, description="API key for external provider")

    @field_validator("prompt")
    @classmethod
    def _strip_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("prompt must not be blank")
        return v

    @field_validator("api_key")
    @classmethod
    def _validate_api_key(cls, v: SecretStr | None) -> SecretStr | None:
        if v is None:
            return v
        secret = v.get_secret_value() if isinstance(v, SecretStr) else str(v)
        if not secret.strip():
            raise ValueError("api_key must not be blank when provided")
        if len(secret) > 500:
            raise ValueError("api_key too long")
        return v


class NFTResponse(BaseModel):
    status: str = Field(..., description="Status of NFT generation")
    image_url: str = Field(..., description="Data URL or image URL of generated NFT")
    prompt: str = Field(..., description="Prompt used for generation")


class FractalParams(BaseModel):
    c_re: float
    c_im: float
    zoom: float
    max_iter: int
    palette_choice: str

    @field_validator("c_re", "c_im")
    @classmethod
    def validate_complex(cls, v: float) -> float:
        if not -2.0 <= v <= 2.0:
            msg = f"Must be between -2.0 and 2.0, got {v}"
            raise ValueError(msg)
        return v

    @field_validator("zoom")
    @classmethod
    def validate_zoom(cls, v: float) -> float:
        if not 0.5 <= v <= 5.0:
            msg = f"Must be between 0.5 and 5.0, got {v}"
            raise ValueError(msg)
        return v

    @field_validator("max_iter")
    @classmethod
    def validate_max_iter(cls, v: int) -> int:
        if not 20 <= v <= 200:
            msg = f"Must be between 20 and 200, got {v}"
            raise ValueError(msg)
        return v

    @field_validator("palette_choice")
    @classmethod
    def validate_palette(cls, v: str) -> str:
        allowed = {"cool", "warm", "retro", "vibrant", "monochrome"}
        if v not in allowed:
            msg = f"Must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v
