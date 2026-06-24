import os
import time

from app.core.config import Settings


class CatalogService:
    CACHE_TTL = 60

    def __init__(self, settings: Settings):
        self.settings = settings
        self._cat_cache = None
        self._tools_cache = None
        self._cache_ts = 0

    def _is_cache_valid(self):
        return self._cat_cache is not None and (time.time() - self._cache_ts) < self.CACHE_TTL

    def get_categorized_tools(self):
        if self._is_cache_valid():
            return self._cat_cache
        tools_dir = os.path.join(self.settings.TEMPLATES_DIR, "tools")
        category_map = {
            "meme-coin-detector": ("AI & Crypto", "Check if a crypto token is a high-risk meme coin or rug pull"),
            "nft-generator-ai": ("AI & Crypto", "Plan NFT collections with metadata and rarity estimates"),
            "crypto-trend-analyzer": ("AI & Crypto", "Analyze market trends and token sentiment"),
            "crypto-price-prediction": ("AI & Crypto", "Forecast future crypto token prices using AI models"),
            "crypto-fear-greed-index-tracker": ("AI & Crypto", "Track crypto market sentiment with the Fear & Greed Index. See if investors are fearful or greedy"),
            "crypto-profit-calculator": ("AI & Crypto", "Calculate potential gains and profits on crypto trades"),
            "crypto-password-generator": ("AI & Crypto", "Generate cryptographically secure passwords and keys"),
            "airdrop-finder": ("AI & Crypto", "Browse active and upcoming crypto airdrops with requirements and estimated values"),
            "crypto-mining-calculator": ("AI & Crypto", "Estimate mining profitability based on hash rate and power consumption"),
            "crypto-halving-countdown": ("AI & Crypto", "Track countdown to the next Bitcoin halving event with live timer and block progress"),
            "crypto-dca-calculator": ("AI & Crypto", "Simulate Dollar Cost Average strategies for crypto. See how regular investments grow over time"),
            "crypto-scam-checker": ("AI & Crypto", "Check crypto addresses and projects for scams"),
            "crypto-price-converter": ("AI & Crypto", "Convert real-time prices between cryptocurrencies and fiat"),
            "crypto-tax-calculator": ("AI & Crypto", "Calculate your cryptocurrency taxes and capital gains"),
            "crypto-portfolio-analyzer": ("AI & Crypto", "Analyze your cryptocurrency holdings, cost basis, allocation weights, and ROI"),
            "wallet-address-tracker": ("AI & Crypto", "Track wallet balances and portfolio value"),
            "image-background-remover": ("Image Processing", "Remove backgrounds from images instantly online"),
            "image-compressor": ("Image Processing", "Reduce image file size while maintaining high quality"),
            "image-converter": ("Image Processing", "Convert images between PNG, JPG, WebP, and other formats"),
            "meme-generator": ("Image Processing", "Create and share custom memes using premium layouts"),
            "watermark-remover": ("Image Processing", "Remove watermarks from photos cleanly online"),
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
            "debt-calculator": ("Calculators", "Compare snowball and avalanche debt payoff methods and see when you'll be debt-free"),
            "credit-utilization-calculator": ("Calculators", "Determine credit utilization ratio for credit cards"),
            "loan-affordability-calculator": ("Calculators", "Calculate maximum loan amounts based on monthly budget"),
            "mortgage-overpayment-calculator": ("Calculators", "Calculate interest savings from mortgage overpayments"),
            "salary-calculator": ("Calculators", "Convert hourly wage to weekly, monthly, and annual salary"),
            "fd-calculator": ("Calculators", "Calculate Fixed Deposit interest earnings and maturity amounts"),
            "date-calculator": ("Calculators", "Add or subtract days, weeks, months, or years from a date"),
            "eway-bill-calculator": ("Calculators", "Calculate E-Way Bill distance limits and validity criteria"),
            "sip-calculator": ("Calculators", "Calculate mutual fund SIP returns and maturity values"),
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
            "job-card-generator": ("Business & Operations", "Create professional job cards and work orders for service technicians and mechanics"),
            "invoice-generator": ("Business & Operations", "Create and download professional PDF invoices online"),
            "receipt-generator": ("Business & Operations", "Generate custom POS and sales receipts instantly"),
            "purchase-order-generator": ("Business & Operations", "Create professional purchase orders with logo, theme, and print/PDF download"),
            "sales-order-generator": ("Business & Operations", "Create professional sales orders with logo, theme, and print/PDF download"),
            "service-order-generator": ("Business & Operations", "Generate professional service orders with instant cost calculation"),
            "work-order-generator": ("Business & Operations", "Create instant work orders with cost breakdown for maintenance and repairs"),
            "ad-performance-analyzer": ("Business & Operations", "Measure ad campaign ROAS, CTR, CPC, CPA, and conversion rates"),
            "product-performance-analyzer": ("Business & Operations", "Analyze ecommerce product profit margins and break-even ROI"),
            "password-generator": ("Productivity & Utilities", "Create strong, secure random passwords for accounts"),
            "pdf-converter": ("Productivity & Utilities", "Convert images and office files to and from PDF format"),
            "resume-analyzer": ("Productivity & Utilities", "Analyze your resume against ATS tracking algorithms"),
            "resume-generator": ("Productivity & Utilities", "Build a professional, modern resume using premium templates"),
            "task-manager": ("Productivity & Utilities", "Organize tasks and projects using a Kanban board"),
            "time-tracker": ("Productivity & Utilities", "Track work hours and generate simple invoice logs"),
            "note-organizer": ("Productivity & Utilities", "Write, save, and organize notes locally in your browser"),
            "habit-tracker": ("Productivity & Utilities", "Track daily routines and build positive habits"),
            "text-case-converter": ("Productivity & Utilities", "Convert text to uppercase, lowercase, titlecase, and more"),
            "unit-converter": ("Productivity & Utilities", "Convert length, mass, volume, temperature, and other units"),
            "timezone-converter": ("Productivity & Utilities", "Compare and convert time zones around the world"),
            "random-number-generator": ("Productivity & Utilities", "Generate random integers within a custom range"),
            "expense-tracker": ("Productivity & Utilities", "Track daily expenses and monitor personal budget metrics"),
            "love-calculator": ("Productivity & Utilities", "Calculate love compatibility and name matching percentages online"),
        }

        categorized_tools = {}
        if os.path.exists(tools_dir):
            for f in os.listdir(tools_dir):
                if f.endswith(".html"):
                    slug = f[:-5].replace("_", "-")
                    name = slug.replace("-", " ").title()
                    category, desc = category_map.get(slug, ("Other Utilities", f"Free online {name} utility"))
                    if category not in categorized_tools:
                        categorized_tools[category] = []
                    categorized_tools[category].append({"name": name, "url": f"/tool/{slug}", "desc": desc})

        sorted_categorized = {}
        for cat in sorted(categorized_tools.keys()):
            sorted_categorized[cat] = sorted(categorized_tools[cat], key=lambda x: x["name"])

        static_pages = []
        pages_dir = os.path.join(self.settings.TEMPLATES_DIR, "pages")
        if os.path.exists(pages_dir):
            for f in os.listdir(pages_dir):
                if f.endswith(".html") and f != "sitemap.html":
                    name = f[:-5].replace("-", " ").title()
                    static_pages.append({"name": name, "url": f"/{f[:-5]}"})
        static_pages.sort(key=lambda x: x["name"])

        self._cat_cache = (sorted_categorized, static_pages)
        self._cache_ts = time.time()
        return sorted_categorized, static_pages

    def get_valid_tools(self):
        if self._is_cache_valid() and self._tools_cache is not None:
            return self._tools_cache
        tools_dir = os.path.join(self.settings.TEMPLATES_DIR, "tools")
        if not os.path.exists(tools_dir):
            self._tools_cache = []
            return []
        result = [f[:-5].replace("_", "-") for f in os.listdir(tools_dir) if f.endswith(".html")]
        self._tools_cache = result
        self._cache_ts = time.time()
        return result
