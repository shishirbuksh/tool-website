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
