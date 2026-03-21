import base64
import qrcode
import io
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse, Response
import datetime
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

app = FastAPI(title="Multi-Tool Website")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure directories exist
try:
    os.makedirs(os.path.join(BASE_DIR, "static", "css"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static", "js"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "templates", "tools"), exist_ok=True)
except OSError:
    pass  # Allow serverless/read-only production environments to proceed

# Mount static folder
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

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
