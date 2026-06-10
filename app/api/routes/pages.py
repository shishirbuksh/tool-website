import os
import datetime
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings

router = APIRouter()

# Templates setup
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html"
    )

@router.get("/tool/{tool_name}", response_class=HTMLResponse)
async def get_tool(request: Request, tool_name: str):
    tools_dir = os.path.join(settings.TEMPLATES_DIR, "tools")
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

@router.get("/sitemap", response_class=HTMLResponse)
async def html_sitemap(request: Request):
    category_map = {
        # AI & Crypto
        "crypto-price-prediction": ("AI & Crypto", "Forecast future crypto token prices using AI models"),
        "crypto-trend-analyzer": ("AI & Crypto", "Analyze market trends and token sentiment"),
        "nft-generator-ai": ("AI & Crypto", "Create custom NFT art using AI generators"),
        "crypto-fear-greed-index-tracker": ("AI & Crypto", "Track real-time crypto market fear and greed index"),
        "crypto-profit-calculator": ("AI & Crypto", "Calculate potential gains and profits on crypto trades"),
        "crypto-tax-calculator": ("AI & Crypto", "Estimate capital gains taxes for cryptocurrency transactions"),
        "crypto-password-generator": ("AI & Crypto", "Generate cryptographically secure passwords and keys"),
        "wallet-address-tracker": ("AI & Crypto", "Track wallet balances and transaction histories"),
        "meme-coin-detector": ("AI & Crypto", "Scan and identify high-risk meme coin contracts"),
        "airdrop-finder": ("AI & Crypto", "Find active and upcoming cryptocurrency airdrops"),
        "crypto-halving-countdown": ("AI & Crypto", "Track countdown to the next Bitcoin halving event"),
        "crypto-mining-calculator": ("AI & Crypto", "Estimate mining profitability based on hash rate and power"),
        "crypto-dca-calculator": ("AI & Crypto", "Simulate Dollar Cost Average strategies for crypto"),
        "crypto-scam-checker": ("AI & Crypto", "Check crypto addresses and projects for scams"),
        "crypto-price-converter": ("AI & Crypto", "Convert real-time prices between cryptocurrencies and fiat"),
        "crypto-portfolio-analyzer": ("AI & Crypto", "Analyze your cryptocurrency holdings, cost basis, allocation weights, and ROI"),
        
        # Image Tools
        "image-background-remover": ("Image Processing", "Remove backgrounds from images instantly online"),
        "image-compressor": ("Image Processing", "Reduce image file size while maintaining high quality"),
        "image-converter": ("Image Processing", "Convert images between PNG, JPG, WebP, and other formats"),
        "meme-generator": ("Image Processing", "Create and share custom memes using premium layouts"),
        "watermark-remover": ("Image Processing", "Remove watermarks from photos cleanly online"),
        
        # Calculators
        "scientific-calculator": ("Calculators", "Solve advanced mathematical and scientific equations online"),
        "calculator": ("Calculators", "Simple, fast standard calculator for everyday math"),
        "percentage-calculator": ("Calculators", "Calculate percentages, increases, decreases, and fractions"),
        "age-calculator": ("Calculators", "Calculate your exact age in years, months, weeks, and days"),
        "profit-margin-calculator": ("Calculators", "Determine sales revenue, profit margin, and markup"),
        "mrr-calculator": ("Calculators", "Calculate SaaS Monthly Recurring Revenue growth metrics"),
        "cac-calculator": ("Calculators", "Calculate Customer Acquisition Cost for marketing campaigns"),
        "burn-rate-calculator": ("Calculators", "Track cash runway and monthly cash burn rates for startups"),
        "gst-calculator": ("Calculators", "Calculate Goods and Services Tax (GST) for products and services"),
        "emi-calculator": ("Calculators", "Estimate monthly loan repayments (Equated Monthly Installment)"),
        "adsense-calculator": ("Calculators", "Estimate Google AdSense earnings based on page views and CTR"),
        "instagram-calculator": ("Calculators", "Calculate Instagram engagement rates and post earnings"),
        "youtube-calculator": ("Calculators", "Estimate YouTube channel earnings based on views and RPM"),
        "compound-calculator": ("Calculators", "Calculate compound interest gains over time"),
        "credit-utilization-calculator": ("Calculators", "Determine credit utilization ratio for credit cards"),
        "loan-affordability-calculator": ("Calculators", "Calculate maximum loan amounts based on monthly budget"),
        "mortgage-overpayment-calculator": ("Calculators", "Calculate interest savings from mortgage overpayments"),
        "debt-calculator": ("Calculators", "Create customized debt payoff schedules and strategies"),
        "salary-calculator": ("Calculators", "Convert hourly wage to weekly, monthly, and annual salary"),
        "fd-calculator": ("Calculators", "Calculate Fixed Deposit interest earnings and maturity amounts"),
        "date-calculator": ("Calculators", "Add or subtract days, weeks, months, or years from a date"),
        "eway-bill-calculator": ("Calculators", "Calculate E-Way Bill distance limits and validity criteria"),
        "sip-calculator": ("Calculators", "Calculate mutual fund SIP returns and maturity values"),
        
        # Developer & SEO
        "api-tester": ("Developer & SEO", "Test REST APIs and HTTP requests directly from your browser"),
        "base64-tool": ("Developer & SEO", "Encode and decode text and files using Base64 format"),
        "uuid-generator": ("Developer & SEO", "Generate random UUID v1 and v4 strings for development"),
        "qr-generator": ("Developer & SEO", "Generate high-quality custom QR codes online"),
        "meta-tag-generator": ("Developer & SEO", "Create SEO-friendly meta tags for websites"),
        "open-graph-generator": ("Developer & SEO", "Generate Open Graph meta tags for social media previews"),
        "robots-txt-generator": ("Developer & SEO", "Create custom robots.txt files for search engine crawlers"),
        "schema-generator": ("Developer & SEO", "Generate structured JSON-LD schema markup for SEO"),
        "sitemap-generator": ("Developer & SEO", "Generate XML sitemaps for search engine indexing"),
        "keyword-data-analyzer": ("Developer & SEO", "Analyze keyword density ratios, cluster search terms, and detect keyword stuffing warnings"),
        
        # Business & Operations
        "invoice-generator": ("Business & Operations", "Create and download professional PDF invoices online"),
        "receipt-generator": ("Business & Operations", "Generate custom POS and sales receipts instantly"),
        "purchase-order-generator": ("Business & Operations", "Create official PDF Purchase Orders for business transactions"),
        "sales-order-generator": ("Business & Operations", "Generate professional PDF Sales Orders for sales tracking"),
        "job-card-generator": ("Business & Operations", "Create and track service repair job cards for mechanics"),
        "service-order-generator": ("Business & Operations", "Generate custom PDF service orders for contractors"),
        "work-order-generator": ("Business & Operations", "Create official business work orders and service requests"),
        
        # Productivity & Utilities
        "password-generator": ("Productivity & Utilities", "Create strong, secure random passwords for accounts"),
        "pdf-converter": ("Productivity & Utilities", "Convert images and office files to and from PDF format"),
        "resume-analyzer": ("Productivity & Utilities", "Analyze your resume against ATS tracking algorithms"),
        "resume-generator": ("Productivity & Utilities", "Build a professional, modern resume using premium templates"),
        "task-manager": ("Productivity & Utilities", "Organize tasks and projects using a Kanban board"),
        "time-tracker": ("Productivity & Utilities", "Track work hours and generate simple invoice logs"),
        "note-organizer": ("Productivity & Utilities", "Write, save, and organize notes locally in your browser"),
        "text-case-converter": ("Productivity & Utilities", "Convert text to uppercase, lowercase, titlecase, and more"),
        "unit-converter": ("Productivity & Utilities", "Convert length, mass, volume, temperature, and other units"),
        "timezone-converter": ("Productivity & Utilities", "Compare and convert time zones around the world"),
        "random-number-generator": ("Productivity & Utilities", "Generate random integers within a custom range"),
        "expense-tracker": ("Productivity & Utilities", "Track daily expenses and monitor personal budget metrics"),
        "love-calculator": ("Productivity & Utilities", "Calculate love compatibility and name matching percentages online")
    }

    categorized_tools = {}
    tools_dir = os.path.join(settings.TEMPLATES_DIR, "tools")
    if os.path.exists(tools_dir):
        for f in os.listdir(tools_dir):
            if f.endswith(".html"):
                slug = f[:-5].replace('_', '-')
                name = slug.replace('-', ' ').title()
                category, desc = category_map.get(slug, ("Other Utilities", f"Free online {name} utility"))
                
                if category not in categorized_tools:
                    categorized_tools[category] = []
                categorized_tools[category].append({
                    "name": name,
                    "url": f"/tool/{slug}",
                    "desc": desc
                })

    sorted_categorized = {}
    for cat in sorted(categorized_tools.keys()):
        sorted_categorized[cat] = sorted(categorized_tools[cat], key=lambda x: x["name"])

    static_pages = []
    pages_dir = os.path.join(settings.TEMPLATES_DIR, "pages")
    if os.path.exists(pages_dir):
        for f in os.listdir(pages_dir):
            if f.endswith(".html") and f != "sitemap.html":
                name = f[:-5].replace('-', ' ').title()
                static_pages.append({"name": name, "url": f"/{f[:-5]}"})
    static_pages.sort(key=lambda x: x["name"])

    return templates.TemplateResponse(
        request=request,
        name="pages/sitemap.html",
        context={
            "title": "HTML Sitemap — StoryBrain AI",
            "categories": sorted_categorized,
            "static_pages": static_pages
        }
    )


@router.get("/{page_name}", response_class=HTMLResponse)
async def get_page(request: Request, page_name: str):
    pages_dir = os.path.join(settings.TEMPLATES_DIR, "pages")
    valid_pages = [f[:-5] for f in os.listdir(pages_dir) if f.endswith('.html')] if os.path.exists(pages_dir) else []
    
    if page_name in valid_pages:
        return templates.TemplateResponse(request=request, name=f"pages/{page_name}.html", context={"title": page_name.replace('-', ' ').title()})
    return HTMLResponse(status_code=404, content="Page not found")

