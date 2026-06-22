import asyncio
import base64
import hashlib
import io
import json
import time

import requests
from PIL import Image, ImageOps

try:
    import rust_predictor
except Exception:
    rust_predictor = None

from app.core.config import Settings
from app.core.exceptions import ServiceError, ValidationException
from app.core.log import get_logger
from app.models import FractalParams

logger = get_logger(__name__)


class FractalService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._session = requests.Session()

    async def generate_nft(self, prompt: str, style: str = "3d", provider: str = "local",
                           api_key: str = None) -> dict:
        if rust_predictor is None:
            raise ServiceError("rust_predictor module is not available")

        width, height = 512, 512
        zoom = 1.0
        c_re, c_im = 0.0, 0.0
        max_iter = 50
        palette_choice = "vibrant"

        if provider == "local":
            h = hashlib.sha256(f"{prompt}_{style}_{time.time() // 10}".encode()).hexdigest()
            zoom = max(0.5, (int(h[0:2], 16) / 255.0) * 3.0)
            c_re = (int(h[2:4], 16) / 255.0) * 2.0 - 1.0
            c_im = (int(h[4:6], 16) / 255.0) * 2.0 - 1.0
            max_iter = max(50, int((int(h[6:8], 16) / 255.0) * 200))

            if style == "cyberpunk":
                c_re, c_im = -0.8, 0.156
                palette_choice = "cool"
            elif style == "3d":
                c_re, c_im = 0.285, 0.01
                palette_choice = "warm"
            elif style == "pixel":
                max_iter = 30
                zoom = 1.0
                width, height = 128, 128
                palette_choice = "retro"
            else:
                palette_choice = "monochrome" if int(h[8], 16) % 2 == 0 else "vibrant"
        else:
            if not api_key:
                raise ValidationException(f"API Key required for provider: {provider}")

            system_prompt = (
                "You are an orchestration AI for a procedural Rust NFT generator. "
                "Translate the user's prompt and style into a purely structural JSON object "
                "WITHOUT markdown blocks or formatting. Required JSON format: "
                '{"c_re": float (-2.0 to 2.0), "c_im": float (-2.0 to 2.0), '
                '"zoom": float (0.5 to 5.0), "max_iter": int (20 to 200), '
                '"palette_choice": string ("cool", "warm", "retro", "vibrant", "monochrome")} '
                "Respond ONLY with raw JSON mechanics."
            )
            user_content = f"Prompt: {prompt}, Style: {style}"

            try:
                llm_text = await self._call_llm(provider, api_key, system_prompt, user_content)
                llm_text = llm_text.replace("```json", "").replace("```", "").strip()
                params = FractalParams(**json.loads(llm_text))
                c_re, c_im = params.c_re, params.c_im
                zoom, max_iter = params.zoom, params.max_iter
                palette_choice = params.palette_choice

                if style == "pixel":
                    width, height = 128, 128
            except json.JSONDecodeError as e:
                raise ServiceError(f"LLM returned invalid JSON: {str(e)}")
            except Exception as e:
                raise ServiceError(f"LLM Orchestration error: {str(e)}")

        raw_data = await self._generate_pattern(width, height, zoom, c_re, c_im, max_iter)

        img = Image.new("L", (width, height))
        img.putdata(raw_data)

        if style == "pixel":
            img = img.resize((512, 512), Image.NEAREST)

        palette_map = {
            "cool": ("#0f0c29", "#302b63", "#24243e"),
            "warm": ("#200000", "#ff416c", "#ff4b2b"),
            "retro": ("#000000", "#00ff00", "#ffffff"),
            "vibrant": ("#8A2387", "#E94057", "#F27121"),
        }
        palette = palette_map.get(palette_choice)
        if palette:
            img_color = ImageOps.colorize(img, black=palette[0], mid=palette[1], white=palette[2])
        else:
            img_color = img.convert("RGB")

        img_byte_arr = io.BytesIO()
        img_color.save(img_byte_arr, format="PNG")
        b64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        return {"status": "success", "image_url": data_url, "prompt": prompt}

    async def _call_llm(self, provider: str, api_key: str, system_prompt: str, user_content: str) -> str:
        loop = asyncio.get_running_loop()

        endpoints = {
            "openai": {
                "url": "https://api.openai.com/v1/chat/completions",
                "headers": {"Authorization": f"Bearer {api_key}"},
                "json": {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                },
                "parse": lambda resp: resp.json()["choices"][0]["message"]["content"],
            },
            "deepseek": {
                "url": "https://api.deepseek.com/chat/completions",
                "headers": {"Authorization": f"Bearer {api_key}"},
                "json": {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                },
                "parse": lambda resp: resp.json()["choices"][0]["message"]["content"],
            },
            "gemini": {
                "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                "headers": {"x-goog-api-key": api_key},
                "json": {
                    "contents": [
                        {"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_content}]}
                    ],
                },
                "parse": lambda resp: resp.json()["candidates"][0]["content"]["parts"][0]["text"],
            },
        }

        if provider not in endpoints:
            raise ValidationException(f"Unknown provider: {provider}")

        cfg = endpoints[provider]

        def _request():
            resp = self._session.post(cfg["url"], headers=cfg["headers"], json=cfg["json"], timeout=30)
            if resp.status_code != 200:
                raise ServiceError(f"{provider} error: {resp.text}")
            return cfg["parse"](resp)

        return await loop.run_in_executor(None, _request)

    async def _generate_pattern(self, width: int, height: int, zoom: float,
                                c_re: float, c_im: float, max_iter: int) -> list:
        loop = asyncio.get_running_loop()

        def _gen():
            return rust_predictor.generate_pattern(width, height, zoom, c_re, c_im, max_iter)

        return await loop.run_in_executor(None, _gen)
