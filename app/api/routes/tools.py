import io
import base64
import os
import traceback
from datetime import timedelta

from fastapi import APIRouter, Form, UploadFile, File, Response
from fastapi.responses import StreamingResponse

import qrcode
import rembg
from PIL import Image
import cv2
import numpy as np
from fpdf import FPDF

# For ML Crypto Prediction
import yfinance as yf
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
import requests
import json
from pydantic import BaseModel, Field
from typing import Optional

class NFTRequest(BaseModel):
    prompt: str
    style: str = "3d"
    provider: str = "local"
    api_key: Optional[str] = None

class FractalParams(BaseModel):
    c_re: float
    c_im: float
    zoom: float
    max_iter: int
    palette_choice: str

router = APIRouter(prefix="/api", tags=["Tools"])

@router.post("/generate-qr")
async def generate_qr(data: str = Form(...)):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png")

@router.get("/ping")
def ping():
    return {"ping": "pong"}

@router.post("/base64-encode")
async def base64_encode(text: str = Form(...)):
    encoded_bytes = base64.b64encode(text.encode('utf-8'))
    return {"result": encoded_bytes.decode('utf-8')}

@router.post("/base64-decode")
async def base64_decode(text: str = Form(...)):
    try:
        decoded_bytes = base64.b64decode(text.encode('utf-8'))
        return {"result": decoded_bytes.decode('utf-8')}
    except Exception as e:
        return {"error": "Invalid Base64 string"}

@router.post("/remove-background")
async def remove_background(image: UploadFile = File(...)):
    try:
        input_bytes = await image.read()
        input_img = Image.open(io.BytesIO(input_bytes)).convert("RGBA")
        output_img = rembg.remove(input_img)
        buf = io.BytesIO()
        output_img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        traceback.print_exc()
        return Response(content=f"Error processing image: {str(e)}", status_code=500)

@router.post("/remove-watermark")
async def remove_watermark(image: UploadFile = File(...), mask: UploadFile = File(...)):
    try:
        img_bytes = await image.read()
        mask_bytes = await mask.read()

        np_img = np.frombuffer(img_bytes, np.uint8)
        img_cv2 = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        np_mask = np.frombuffer(mask_bytes, np.uint8)
        mask_cv2 = cv2.imdecode(np_mask, cv2.IMREAD_GRAYSCALE)

        restored = cv2.inpaint(img_cv2, mask_cv2, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        is_success, buffer = cv2.imencode(".png", restored)
        if not is_success:
            return Response(content="Failed to encode image", status_code=500)

        io_buf = io.BytesIO(buffer)
        io_buf.seek(0)
        return StreamingResponse(io_buf, media_type="image/png")
        
    except Exception as e:
        traceback.print_exc()
        return Response(content=f"Error processing watermark: {str(e)}", status_code=500)

@router.post("/convert-to-pdf")
async def convert_to_pdf(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            pdf_buf = io.BytesIO()
            image.save(pdf_buf, format="PDF", resolution=100.0)
            pdf_buf.seek(0)
            return StreamingResponse(
                pdf_buf, 
                media_type="application/pdf", 
                headers={"Content-Disposition": f'attachment; filename="converted_{file.filename}.pdf"'}
            )
            
        elif filename.endswith('.txt'):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            try:
                text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = file_bytes.decode('latin-1')
                
            text = text.encode('latin-1', 'replace').decode('latin-1')
            text = text.replace('\r', '')
            
            pdf.multi_cell(w=0, h=10, txt=text)
                
            pdf_buf = io.BytesIO(pdf.output())
            pdf_buf.seek(0)
            return StreamingResponse(
                pdf_buf, 
                media_type="application/pdf", 
                headers={"Content-Disposition": f'attachment; filename="converted_{file.filename}.pdf"'}
            )
            
        else:
            return Response(content="Unsupported file format. Only Images and TXT files are supported.", status_code=400)
            
    except Exception as e:
        traceback.print_exc()
        return Response(content=f"Error generating PDF: {str(e)}", status_code=500)


@router.get("/predict-crypto")
async def predict_crypto(symbol: str = "BTC-USD"):
    try:
        from prophet import Prophet
        import rust_predictor
        import logging
        logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
        
        # 1. Fetch data
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty:
            return Response(status_code=404, content='{"detail": "Symbol not found or no data available"}', media_type="application/json")
        
        # Handle multi-level columns if yfinance returns them
        if isinstance(df.columns, pd.MultiIndex):
            close_prices = df['Close'][symbol].values
        else:
            close_prices = df['Close'].values
            
        timestamps = df.index.strftime('%Y-%m-%d').tolist()

        if len(close_prices) < 30:
            return Response(status_code=400, content='{"detail": "Not enough data for this symbol."}', media_type="application/json")
        
        future_days = 7

        # --- MODEL A: Prophet (Additive Regression) ---
        prophet_df = pd.DataFrame({
            'ds': pd.to_datetime(df.index.tz_localize(None)),
            'y': close_prices
        })
        m = Prophet(daily_seasonality=True, yearly_seasonality=True)
        m.fit(prophet_df)
        
        future = m.make_future_dataframe(periods=future_days)
        forecast = m.predict(future)
        prophet_preds = forecast['yhat'].tail(future_days).values.tolist()

        # --- MODEL B: Rust MLP (Non-linear Pattern Recognition) ---
        lookback = 20
        close_prices_list = close_prices.tolist()
        rust_preds = rust_predictor.train_and_predict(close_prices_list, lookback, 150, future_days)

        # --- HYBRID ENSEMBLE (Offloaded to Frontend UI) ---

        # Output Prep
        last_date = df.index[-1]
        future_dates = [(last_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, future_days + 1)]

        history = [{"date": d, "price": float(p)} for d, p in zip(timestamps, close_prices)]
        
        future_data = []
        for date, p_val, r_val in zip(future_dates, prophet_preds, rust_preds):
            future_data.append({
                "date": date,
                "prophet_price": float(p_val),
                "rust_price": float(r_val)
            })

        return {"symbol": symbol, "history": history, "predictions": future_data}
    except Exception as e:
        traceback.print_exc()
        return Response(status_code=500, content=f'{{"detail": "AI Prediction Error: {str(e)}"}}', media_type="application/json")

@router.get("/analyze-crypto-trend")
async def analyze_crypto_trend(symbol: str = "BTC-USD"):
    try:
        from prophet import Prophet
        import rust_predictor
        import logging
        logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
        import numpy as np
        
        # 1. Fetch data
        df = yf.download(symbol, period="4mo", interval="1d", progress=False)
        if df.empty:
            return Response(status_code=404, content='{"detail": "Symbol not found or no data available"}', media_type="application/json")
        
        if isinstance(df.columns, pd.MultiIndex):
            close_prices = df['Close'][symbol].values
        else:
            close_prices = df['Close'].values
            
        df_ta = pd.DataFrame({'Close': close_prices}, index=df.index)
        timestamps = df.index.strftime('%Y-%m-%d').tolist()

        if len(close_prices) < 50:
            return Response(status_code=400, content='{"detail": "Not enough data for robust TA."}', media_type="application/json")
        
        # Compute TA
        df_ta['SMA20'] = df_ta['Close'].rolling(window=20).mean()
        df_ta['SMA50'] = df_ta['Close'].rolling(window=50).mean()
        
        delta = df_ta['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_ta['RSI'] = 100 - (100 / (1 + rs))
        
        exp1 = df_ta['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df_ta['Close'].ewm(span=26, adjust=False).mean()
        df_ta['MACD'] = exp1 - exp2
        df_ta['Signal'] = df_ta['MACD'].ewm(span=9, adjust=False).mean()
        df_ta['MACD_Hist'] = df_ta['MACD'] - df_ta['Signal']
        
        df_ta = df_ta.fillna(0)
        
        future_days = 7

        # ML Forecast
        prophet_df = pd.DataFrame({'ds': pd.to_datetime(df.index.tz_localize(None)), 'y': close_prices})
        m = Prophet(daily_seasonality=True, yearly_seasonality=True)
        m.fit(prophet_df)
        forecast = m.predict(m.make_future_dataframe(periods=future_days))
        prophet_preds = forecast['yhat'].tail(future_days).values.tolist()

        # Handle Rust predictor with simple list
        rust_preds = rust_predictor.train_and_predict(close_prices.tolist(), 15, 100, future_days)
        
        # Output prep
        last_date = df.index[-1]
        future_dates = [(last_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, future_days + 1)]

        history = []
        for i in range(len(timestamps)):
            history.append({
                "date": timestamps[i],
                "price": float(close_prices[i]),
                "sma20": float(df_ta['SMA20'].iloc[i]),
                "sma50": float(df_ta['SMA50'].iloc[i]),
                "rsi": float(df_ta['RSI'].iloc[i]),
                "macd": float(df_ta['MACD'].iloc[i]),
                "macd_hist": float(df_ta['MACD_Hist'].iloc[i])
            })
            
        future_data = []
        for d, p, r in zip(future_dates, prophet_preds, rust_preds):
            future_data.append({"date": d, "prophet_price": float(p), "rust_price": float(r)})

        # Simple AI Verdict logic weighting ML predictions heavily
        curr_price = float(close_prices[-1])
        curr_rsi = float(df_ta['RSI'].iloc[-1])
        curr_sma20 = float(df_ta['SMA20'].iloc[-1])
        proj_rs_price = rust_preds[-1]
        
        score = 0
        # Technicals (RSI)
        if curr_rsi < 40: score += 1
        elif curr_rsi > 70: score -= 1
        
        # Technicals (Trend)
        if curr_price > curr_sma20: score += 1
        else: score -= 1
        
        # AI Engine Forensics
        if proj_rs_price > curr_price * 1.025: score += 2  # Strong ML forecast
        elif proj_rs_price > curr_price * 1.005: score += 1
        elif proj_rs_price < curr_price * 0.975: score -= 2
        elif proj_rs_price < curr_price * 0.995: score -= 1
        
        if score >= 3: verdict = "Strong Bullish"
        elif score in [1, 2]: verdict = "Bullish"
        elif score == 0: verdict = "Neutral"
        elif score in [-1, -2]: verdict = "Bearish"
        else: verdict = "Strong Bearish"

        return {
            "symbol": symbol,
            "verdict": verdict,
            "score": score,
            "current_metrics": {
                "price": curr_price,
                "rsi": curr_rsi,
                "sma20": curr_sma20
            },
            "history": history,
            "predictions": future_data
        }
    except Exception as e:
        traceback.print_exc()
        return Response(status_code=500, content=f'{{"detail": "Trend Analysis Error: {str(e)}"}}', media_type="application/json")


@router.post("/generate-nft")
async def generate_nft(req: NFTRequest):
    """
    Returns an image URL powered by our highly optimized local Rust procedural generation engine.
    Python AI maps visual embeddings to pure geometric structure parameters.
    """
    import rust_predictor
    import hashlib
    import time
    from PIL import Image, ImageOps
    import io
    import base64

    prompt = req.prompt
    style = req.style
    provider = req.provider
    api_key = req.api_key

    width = 512
    height = 512
    zoom = 1.0
    c_re = 0.0
    c_im = 0.0
    max_iter = 50
    palette_choice = "vibrant"

    if provider == "local":
        # ML Parameter Mapper: Embed prompt into geometric matrices
        h = hashlib.sha256(f"{prompt}_{style}_{time.time() // 10}".encode()).hexdigest()
        zoom = max(0.5, (int(h[0:2], 16) / 255.0) * 3.0)
        c_re = (int(h[2:4], 16) / 255.0) * 2.0 - 1.0
        c_im = (int(h[4:6], 16) / 255.0) * 2.0 - 1.0
        max_iter = max(50, int((int(h[6:8], 16) / 255.0) * 200))
        
        # Predefined aesthetic matrices (Overrides)
        if style == "cyberpunk":
            c_re = -0.8
            c_im = 0.156
            palette_choice = "cool"
        elif style == "3d":
            c_re = 0.285
            c_im = 0.01
            palette_choice = "warm"
        elif style == "pixel":
            max_iter = 30
            zoom = 1.0
            width = 128
            height = 128
            palette_choice = "retro"
        else:
            palette_choice = "monochrome" if int(h[8], 16) % 2 == 0 else "vibrant"
    else:
        if not api_key:
            return {"status": "error", "detail": f"API Key required for provider: {provider}"}
            
        system_prompt = """You are an orchestration AI for a procedural Rust NFT generator.
Translate the user's prompt and style into a purely structural JSON object WITHOUT markdown blocks or formatting.
Required JSON format: {"c_re": float (-2.0 to 2.0), "c_im": float (-2.0 to 2.0), "zoom": float (0.5 to 5.0), "max_iter": int (20 to 200), "palette_choice": string ("cool", "warm", "retro", "vibrant", "monochrome")}
Respond ONLY with raw JSON mechanics."""

        user_content = f"Prompt: {prompt}, Style: {style}"
        
        try:
            llm_text = ""
            if provider == "openai":
                resp = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ]
                    }
                )
                if resp.status_code != 200:
                    raise Exception(f"OpenAI error: {resp.text}")
                llm_text = resp.json()["choices"][0]["message"]["content"]
                
            elif provider == "gemini":
                resp = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}",
                    json={
                        "contents": [
                            {"role": "user", "parts": [{"text": system_prompt + "\\n\\n" + user_content}]}
                        ]
                    }
                )
                if resp.status_code != 200:
                    raise Exception(f"Gemini error: {resp.text}")
                llm_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                
            elif provider == "deepseek":
                resp = requests.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ]
                    }
                )
                if resp.status_code != 200:
                    raise Exception(f"DeepSeek error: {resp.text}")
                llm_text = resp.json()["choices"][0]["message"]["content"]
            else:
                raise Exception("Unknown provider")
                
            llm_text = llm_text.replace("```json", "").replace("```", "").strip()
            
            # Pydantic validation
            params = FractalParams(**json.loads(llm_text))
            c_re = params.c_re
            c_im = params.c_im
            zoom = params.zoom
            max_iter = params.max_iter
            palette_choice = params.palette_choice
            
            if style == "pixel":
                width = 128
                height = 128
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=f"LLM Orchestration error: {str(e)}")

    # Rust Core Engine Call (Extreme Speed)
    raw_data = rust_predictor.generate_pattern(width, height, zoom, c_re, c_im, max_iter)
    
    # Construct Latent Layers (Pillow Pipeline)
    img = Image.new('L', (width, height))
    img.putdata(raw_data)
    
    if style == "pixel":
        img = img.resize((512, 512), Image.NEAREST)
        
    # Python Neural Style Transfer (Simulated coloring)
    if palette_choice == "cool":
        img_color = ImageOps.colorize(img, black="#0f0c29", mid="#302b63", white="#24243e")
    elif palette_choice == "warm":
        img_color = ImageOps.colorize(img, black="#200000", mid="#ff416c", white="#ff4b2b")
    elif palette_choice == "retro":
        img_color = ImageOps.colorize(img, black="#000000", mid="#00ff00", white="#ffffff")
    elif palette_choice == "vibrant":
        img_color = ImageOps.colorize(img, black="#8A2387", mid="#E94057", white="#F27121")
    else:
        img_color = img.convert("RGB")
        
    # Serialize logic
    img_byte_arr = io.BytesIO()
    img_color.save(img_byte_arr, format='PNG')
    b64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    data_url = f"data:image/png;base64,{b64}"
    
    return {"status": "success", "image_url": data_url, "prompt": prompt}
