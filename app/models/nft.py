"""Pydantic models for NFT generation and fractal parameter validation."""

from pydantic import BaseModel, Field, field_validator


class NFTRequest(BaseModel):
    prompt: str
    style: str = Field(default="3d", description="Art style for generation")
    provider: str = Field(default="local", description="AI provider (local, openai, gemini, deepseek)")
    api_key: str | None = Field(default=None, description="API key for external provider")


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
