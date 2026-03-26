import base64
import qrcode
import io
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, Response
import datetime
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import rembg
from PIL import Image
import cv2
import numpy as np
from fpdf import FPDF

app = FastAPI(title="Multi-Tool Website")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure directories exist
try:
    os.makedirs(os.path.join(BASE_DIR, "static", "css"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static", "js"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "templates", "tools"), exist_ok=True)
except OSError:
    pass  # Allow serverless/read-only production environments to proceed

# Mount static folder with caching headers
class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

app.mount("/static", CachedStaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html"
    )

@app.get("/tool/{tool_name}", response_class=HTMLResponse)
async def get_tool(request: Request, tool_name: str):
    tools_dir = os.path.join(BASE_DIR, "templates", "tools")
    valid_tools = []
    if os.path.exists(tools_dir):
        valid_tools = [f[:-5].replace('_', '-') for f in os.listdir(tools_dir) if f.endswith('.html')]
        
    if tool_name not in valid_tools:
        return HTMLResponse(status_code=404, content="Tool not found")
    
    template_name = f"tools/{tool_name.replace('-', '_')}.html"
    return templates.TemplateResponse(
        request=request, 
        name=template_name, 
        context={"tool_name": tool_name.replace('-', ' ').title()}
    )

@app.get("/sitemap.xml")
async def sitemap():
    base_url = "https://storybrainai.com"
    
    def get_lastmod(file_path: str) -> str:
        try:
            full_path = os.path.join(BASE_DIR, file_path)
            return datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d")
        except:
            return datetime.datetime.now().strftime("%Y-%m-%d")

    pages = [
        {"url": "/", "file": "templates/index.html", "freq": "weekly", "pri": "1.0"},
    ]
    
    # Dynamically inject tools
    tools_dir = os.path.join(BASE_DIR, "templates", "tools")
    if os.path.exists(tools_dir):
        for f in os.listdir(tools_dir):
            if f.endswith(".html"):
                tool_name = f[:-5].replace('_', '-')
                pages.append({"url": f"/tool/{tool_name}", "file": f"templates/tools/{f}", "freq": "monthly", "pri": "0.8"})
    
    # Dynamically inject static pages
    pages_dir = os.path.join(BASE_DIR, "templates", "pages")
    if os.path.exists(pages_dir):
        for f in os.listdir(pages_dir):
            if f.endswith(".html"):
                page_name = f[:-5]
                # Lower priority for generic static pages like privacy, terms, disclaimer
                pri = "0.2" if page_name in ["privacy", "terms", "disclaimer"] else "0.4"
                pages.append({"url": f"/{page_name}", "file": f"templates/pages/{f}", "freq": "yearly", "pri": pri})
    
    url_tags = []
    for p in pages:
        lastmod = get_lastmod(p["file"])
        url_tags.append(f'    <url><loc>{base_url}{p["url"]}</loc><lastmod>{lastmod}</lastmod><changefreq>{p["freq"]}</changefreq><priority>{p["pri"]}</priority></url>')
        
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml_content += "\n".join(url_tags)
    xml_content += '\n</urlset>'
    
    return Response(content=xml_content, media_type="application/xml")

@app.get("/robots.txt")
async def robots():
    txt = "User-agent: *\nAllow: /\n\nSitemap: https://storybrainai.com/sitemap.xml"
    return Response(content=txt, media_type="text/plain")

@app.get("/{page_name}", response_class=HTMLResponse)
async def get_page(request: Request, page_name: str):
    pages_dir = os.path.join(BASE_DIR, "templates", "pages")
    valid_pages = [f[:-5] for f in os.listdir(pages_dir) if f.endswith('.html')] if os.path.exists(pages_dir) else []
    
    if page_name in valid_pages:
        return templates.TemplateResponse(request=request, name=f"pages/{page_name}.html", context={"title": page_name.title()})
    return HTMLResponse(status_code=404, content="Page not found")

# --- Tool Specific APIs ---

@app.post("/api/generate-qr")
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

@app.get("/api/ping")
def ping():
    return {"ping": "pong"}

@app.post("/api/base64-encode")
async def base64_encode(text: str = Form(...)):
    encoded_bytes = base64.b64encode(text.encode('utf-8'))
    return {"result": encoded_bytes.decode('utf-8')}

@app.post("/api/base64-decode")
async def base64_decode(text: str = Form(...)):
    try:
        decoded_bytes = base64.b64decode(text.encode('utf-8'))
        return {"result": decoded_bytes.decode('utf-8')}
    except Exception as e:
        return {"error": "Invalid Base64 string"}

@app.post("/api/remove-background")
async def remove_background(image: UploadFile = File(...)):
    try:
        # Read the uploaded file bytes into memory
        input_bytes = await image.read()
        
        # Open as PIL Image — more reliable than passing raw bytes directly on Windows
        input_img = Image.open(io.BytesIO(input_bytes)).convert("RGBA")
        
        # Run background removal (rembg accepts and returns PIL Images)
        output_img = rembg.remove(input_img)
        
        # Save result to an in-memory buffer as PNG (keeps transparency)
        buf = io.BytesIO()
        output_img.save(buf, format="PNG")
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(content=f"Error processing image: {str(e)}", status_code=500)

@app.post("/api/remove-watermark")
async def remove_watermark(image: UploadFile = File(...), mask: UploadFile = File(...)):
    try:
        # Read files into bytes
        img_bytes = await image.read()
        mask_bytes = await mask.read()

        # Convert to numpy arrays decoded by cv2
        np_img = np.frombuffer(img_bytes, np.uint8)
        img_cv2 = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        np_mask = np.frombuffer(mask_bytes, np.uint8)
        mask_cv2 = cv2.imdecode(np_mask, cv2.IMREAD_GRAYSCALE)

        # Inpaint using Telea's algorithm
        # The mask must be a single-channel 8-bit image where non-zero pixels indicate area to inpaint.
        restored = cv2.inpaint(img_cv2, mask_cv2, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        # Encode back to PNG
        is_success, buffer = cv2.imencode(".png", restored)
        if not is_success:
            return Response(content="Failed to encode image", status_code=500)

        io_buf = io.BytesIO(buffer)
        return StreamingResponse(io_buf, media_type="image/png")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(content=f"Error processing watermark: {str(e)}", status_code=500)

@app.post("/api/convert-to-pdf")
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
        import traceback
        traceback.print_exc()
        return Response(content=f"Error generating PDF: {str(e)}", status_code=500)

# trigger reload
