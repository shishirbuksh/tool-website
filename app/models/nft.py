from pydantic import BaseModel, Field


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
