import os
import time
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.services.catalog_service import CatalogService


class ToolSEO(BaseModel):
    slug: str
    name: str
    icon: str = "wand-2"
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    app_category: str = "UtilitiesApplication"
    faqs: list[dict] = Field(default_factory=list)
    howto_steps: list[dict] = Field(default_factory=list)
    howto_calculate: str = ""
    about_title: str = ""
    about_body: str = ""
    date_modified: str = ""
    related_slugs: list[str] = Field(default_factory=list)
    related: list[dict] = Field(default_factory=list)


_FAQ_CALC = [
    {"q": "How does the {name} work?", "a": "Simply enter your values into the input fields and click calculate. The tool processes everything instantly in your browser using optimized formulas — no data is sent to any server."},
    {"q": "Is the {name} free to use?", "a": "Yes, it is completely free with no hidden fees, subscriptions, or usage limits. No sign-up or account required."},
    {"q": "How accurate are the results?", "a": "The {name} uses standard mathematical formulas to ensure accurate results. Always double-check critical calculations."},
    {"q": "Is my data safe when using {name}?", "a": "Absolutely. All calculations happen locally in your browser. Your data never touches any server and is never stored or tracked."},
]

_FAQ_CRYPTO = [
    {"q": "Where does the {name} get its data?", "a": "The tool fetches real-time market data from public cryptocurrency APIs to ensure accurate, up-to-date information for your analysis."},
    {"q": "How accurate are the predictions?", "a": "Predictions combine historical data analysis with machine learning models. Crypto markets are volatile, so use predictions as guidance, not financial advice."},
    {"q": "How often is the data refreshed?", "a": "Market data refreshes during your session. Historical analysis uses daily closing prices for consistency."},
    {"q": "Is my data secure?", "a": "Yes. All analysis happens in your browser or through encrypted channels. We never store your wallet addresses or trading data."},
]

_FAQ_IMAGE = [
    {"q": "What file formats are supported?", "a": "We support PNG, JPG, JPEG, WebP, and other common image formats. The tool processes files directly in your browser."},
    {"q": "Is there a file size limit?", "a": "Images up to 10MB are recommended for optimal performance. Larger files may take longer to process depending on your device."},
    {"q": "Does this reduce image quality?", "a": "The tool uses optimized algorithms to maintain the highest possible quality while processing your images."},
    {"q": "Is my image data private?", "a": "Yes. All image processing happens locally on your device. Your images are never uploaded to any server or stored anywhere."},
]

_FAQ_DEV = [
    {"q": "What format is the output?", "a": "The tool generates clean, standards-compliant output that you can copy directly into your project or download as a file."},
    {"q": "Are there any usage limits?", "a": "No. Use the tool as many times as you need. There are no daily limits, rate caps, or premium tiers."},
    {"q": "Does it work offline?", "a": "Once loaded, many features work offline since processing happens client-side. A stable internet connection is needed initially."},
    {"q": "Which browsers are supported?", "a": "Works on all modern browsers including Chrome, Firefox, Safari, and Edge on both desktop and mobile."},
]

_FAQ_BUSINESS = [
    {"q": "Can I download my documents?", "a": "Yes, you can download your generated documents as PDF files directly to your device."},
    {"q": "Is the output legally valid?", "a": "Generated documents are templates for reference. Consult a professional for legally binding documents."},
    {"q": "Can I customize the output?", "a": "Yes, you can customize fields, colors, and layout options before generating your document."},
    {"q": "Is my business data stored?", "a": "No. All data you enter stays in your browser and is never sent to or stored on any server."},
]

_FAQ_PROD = [
    {"q": "Is my data saved between sessions?", "a": "Data is stored locally in your browser using localStorage. Clearing your browser data will remove it."},
    {"q": "Can I lose my data?", "a": "Since data is stored locally, clearing browser data or using a different device will not carry over your information."},
    {"q": "Does this work offline?", "a": "Yes, once loaded, all functionality works entirely offline with no internet connection needed."},
    {"q": "Is my data private?", "a": "Absolutely. Everything stays in your browser. No data is sent to any server or third party."},
]

_HOWTO_CALC = [
    {"title": "Enter Your Values", "desc": "Fill in the input fields with your numbers and select any options relevant to your calculation."},
    {"title": "Click Calculate", "desc": "Press the calculate button to process your inputs instantly using optimized formulas."},
    {"title": "Review Results", "desc": "View your detailed results, copy them to clipboard, or adjust inputs to compare scenarios."},
]

_HOWTO_CRYPTO = [
    {"title": "Select Asset", "desc": "Choose the cryptocurrency or token you want to analyze from the available options."},
    {"title": "Configure Settings", "desc": "Adjust parameters like time period, currency, or analysis depth to match your needs."},
    {"title": "Review Analysis", "desc": "Get instant insights, predictions, and data visualizations to inform your decisions."},
]

_HOWTO_IMAGE = [
    {"title": "Upload Image", "desc": "Select or drag-and-drop your image file. Supported formats include PNG, JPG, and WebP."},
    {"title": "Configure Options", "desc": "Adjust settings like output format, quality, or processing mode to get the result you need."},
    {"title": "Download Result", "desc": "Preview your processed image and download it to your device in your chosen format."},
]

_HOWTO_DEV = [
    {"title": "Enter Input", "desc": "Type or paste your input data into the provided field or configure the options."},
    {"title": "Generate", "desc": "Click the generate button to create your output instantly in the browser."},
    {"title": "Copy or Download", "desc": "Copy the result to your clipboard or download it for use in your project."},
]

_HOWTO_BUSINESS = [
    {"title": "Fill Details", "desc": "Enter your business information, customer details, and line items into the form."},
    {"title": "Customize", "desc": "Adjust the template options, colors, and layout to match your brand."},
    {"title": "Download PDF", "desc": "Generate and download your professional document as a PDF file."},
]

_HOWTO_PROD = [
    {"title": "Set Up", "desc": "Configure the tool by entering your data or adjusting the settings to your preference."},
    {"title": "Use the Tool", "desc": "Interact with the tool to track, organize, or generate content as needed."},
    {"title": "Review & Export", "desc": "View your data, make adjustments, and export or copy results when ready."},
]


CATEGORY_DEFAULTS = {
    "AI & Crypto": {
        "icon": "bitcoin",
        "app_category": "FinanceApplication",
        "faqs": _FAQ_CRYPTO,
        "howto_steps": _HOWTO_CRYPTO,
    },
    "Image Processing": {
        "icon": "image",
        "app_category": "MultimediaApplication",
        "faqs": _FAQ_IMAGE,
        "howto_steps": _HOWTO_IMAGE,
    },
    "Calculators": {
        "icon": "calculator",
        "app_category": "FinanceApplication",
        "faqs": _FAQ_CALC,
        "howto_steps": _HOWTO_CALC,
    },
    "Developer & SEO": {
        "icon": "code",
        "app_category": "DeveloperApplication",
        "faqs": _FAQ_DEV,
        "howto_steps": _HOWTO_DEV,
    },
    "Business & Operations": {
        "icon": "briefcase",
        "app_category": "BusinessApplication",
        "faqs": _FAQ_BUSINESS,
        "howto_steps": _HOWTO_BUSINESS,
    },
    "Productivity & Utilities": {
        "icon": "zap",
        "app_category": "UtilitiesApplication",
        "faqs": _FAQ_PROD,
        "howto_steps": _HOWTO_PROD,
    },
}


OVERRIDES: dict[str, dict[str, Any]] = {
    "calculator": {
        "icon": "calculator",
        "app_category": "UtilitiesApplication",
        "faqs": [
            {"q": "Can I use my keyboard with this calculator?", "a": "Yes. Type numbers with your keyboard, press Enter for equals, Escape to clear, and Backspace to delete the last digit."},
            {"q": "Does this support order of operations?", "a": "This is a standard calculator that performs one operation at a time. For complex calculations, try our Scientific Calculator."},
        ],
        "about_title": "About the Standard Calculator",
        "about_body": "<p>The Standard Calculator is a fast, lightweight browser-based calculator designed for everyday arithmetic. It handles addition, subtraction, multiplication, and division with full keyboard support for power users.</p><p>Unlike native calculator apps, this tool requires no installation, works on any device with a browser, and processes everything locally — your numbers never leave your computer.</p>",
    },
    "scientific-calculator": {
        "icon": "sigma",
        "app_category": "UtilitiesApplication",
    },
    "qr-generator": {
        "icon": "scan-qr-code",
        "app_category": "UtilitiesApplication",
        "faqs": [
            {"q": "Can I download the QR code?", "a": "Yes, click the Download PNG button to save your QR code as a high-quality PNG image."},
            {"q": "What can I put in a QR code?", "a": "URLs, plain text, contact information, WiFi network credentials, and more."},
        ],
        "howto_steps": [
            {"title": "Choose Type", "desc": "Select URL, text, vCard, or WiFi for your QR code content."},
            {"title": "Enter Data", "desc": "Fill in the fields for your chosen QR code type."},
            {"title": "Generate & Download", "desc": "Click Generate then download your QR code as a PNG image."},
        ],
        "about_title": "About the QR Code Generator",
        "about_body": "<p>The QR Code Generator lets you create custom QR codes in seconds. Supports URLs, plain text, vCard contact details, and WiFi network credentials with optional foreground color customization.</p><p>All QR codes are generated entirely in your browser — no uploads, no servers, no tracking. Download your QR code as a high-resolution PNG ready for print or web use.</p>",
    },
    "image-background-remover": {
        "icon": "image",
        "app_category": "MultimediaApplication",
        "faqs": [
            {"q": "How long does background removal take?", "a": "Most images process in seconds. Processing time depends on image size and your device capabilities."},
            {"q": "Can I choose a custom background color?", "a": "Yes. You can select a custom background color or keep the background transparent."},
        ],
        "about_title": "About the Background Remover",
        "about_body": "<p>The Image Background Remover uses advanced AI-based segmentation to detect and remove backgrounds from photos with a single click. Upload any portrait, product shot, or graphic and get a clean cutout instantly.</p><p>You can replace the removed background with a solid color of your choice or keep it transparent for use in design projects. All processing happens locally in your browser — your images are never uploaded.</p>",
    },
    "pdf-converter": {
        "icon": "file-text",
        "app_category": "UtilitiesApplication",
    },
    "password-generator": {
        "icon": "key",
        "app_category": "SecurityApplication",
        "about_title": "About the Password Generator",
        "about_body": "<p>The Password Generator creates strong, cryptographically secure passwords to protect your online accounts. Customize length, character types (uppercase, lowercase, numbers, symbols), and exclude ambiguous characters for readability.</p><p>Passwords are generated entirely in your browser using secure random number generation. No passwords are ever transmitted, stored, or logged.</p>",
    },
    "crypto-price-prediction": {
        "icon": "trending-up",
        "app_category": "FinanceApplication",
    },
    "crypto-trend-analyzer": {
        "icon": "zap",
        "app_category": "FinanceApplication",
    },
    "nft-generator-ai": {
        "icon": "palette",
        "app_category": "MultimediaApplication",
    },
    "schema-generator": {
        "icon": "code",
        "app_category": "DeveloperApplication",
        "faqs": [
            {"q": "What is JSON-LD schema?", "a": "JSON-LD is structured data that helps search engines understand your content and display rich snippets in results."},
        ],
    },
    "api-tester": {
        "icon": "globe",
        "app_category": "DeveloperApplication",
    },
    "invoice-generator": {
        "icon": "file-invoice",
        "app_category": "BusinessApplication",
        "about_title": "About the Invoice Generator",
        "about_body": "<p>The Invoice Generator helps freelancers and small businesses create professional PDF invoices in seconds. Add your company logo, customer details, line items, taxes, and discounts to generate a clean, print-ready invoice.</p><p>All data stays in your browser — nothing is sent to any server. Download your invoice as a PDF file or print directly from the page.</p>",
    },
    "sip-calculator": {
        "icon": "trending-up",
        "app_category": "FinanceApplication",
    },
    "base64-tool": {
        "icon": "terminal",
        "app_category": "DeveloperApplication",
    },
    "uuid-generator": {
        "icon": "fingerprint",
        "app_category": "DeveloperApplication",
    },
    "image-compressor": {
        "icon": "image",
        "app_category": "MultimediaApplication",
    },
    "image-converter": {
        "icon": "image",
        "app_category": "MultimediaApplication",
    },
    "meme-generator": {
        "icon": "smile",
        "app_category": "MultimediaApplication",
    },
    "watermark-remover": {
        "icon": "image",
        "app_category": "MultimediaApplication",
    },
    "resume-generator": {
        "icon": "file",
        "app_category": "BusinessApplication",
    },
    "resume-analyzer": {
        "icon": "search",
        "app_category": "BusinessApplication",
    },
}


class SeoService:
    CACHE_TTL = 300

    def __init__(self, settings: Settings):
        self.settings = settings
        self._catalog = CatalogService(settings)
        self._cat_cache: tuple[float, dict[str, ToolSEO]] | None = None

    def _fill(self, template: Any, name: str, slug: str, category: str, description: str) -> Any:
        if isinstance(template, str):
            return template.replace("{name}", name).replace("{slug}", slug).replace("{category}", category).replace("{description}", description)
        if isinstance(template, list):
            return [self._fill(item, name, slug, category, description) for item in template]
        if isinstance(template, dict):
            return {k: self._fill(v, name, slug, category, description) for k, v in template.items()}
        return template

    def _build_all(self) -> dict[str, ToolSEO]:
        cached = self._cat_cache
        if cached and time.time() - cached[0] < self.CACHE_TTL:
            return cached[1]

        categories, _ = self._catalog.get_categorized_tools()
        result: dict[str, ToolSEO] = {}

        for cat_name, tools in categories.items():
            defaults = CATEGORY_DEFAULTS.get(cat_name, CATEGORY_DEFAULTS["Productivity & Utilities"])
            for t in tools:
                slug = t["url"].split("/tool/")[-1]
                name = t["name"]
                desc = t.get("desc", f"Free online {name.lower()} utility")
                override = OVERRIDES.get(slug, {})

                def merge_list(base: list, override_list: list) -> list:
                    if not override_list:
                        return base
                    return base + override_list

                faqs = merge_list(
                    self._fill(defaults["faqs"], name, slug, cat_name, desc),
                    self._fill(override.get("faqs", []), name, slug, cat_name, desc),
                )
                howto = merge_list(
                    self._fill(defaults["howto_steps"], name, slug, cat_name, desc),
                    self._fill(override.get("howto_steps", []), name, slug, cat_name, desc),
                )

                icon = override.get("icon", defaults["icon"])
                app_category = override.get("app_category", defaults["app_category"])
                keywords = [
                    f"free {name.lower()} online",
                    f"{name.lower()} tool",
                    f"best {name.lower()} without sign up",
                    f"online {name.lower()} free no download",
                    f"{cat_name.lower()} {name.lower()}",
                ]

                about_title = override.get("about_title", f"About the {name}")
                default_about = (
                    f"<p>The {name} is a free online tool that helps you {desc[0].lower() + desc[1:] if desc else 'get things done quickly and efficiently'}.</p>"
                    f"<p>Built with privacy in mind, all processing happens directly in your browser. No sign-up required, no data stored, no tracking. "
                    f"Simply open the tool, enter your information, and get instant results.</p>"
                )
                about_body = override.get("about_body", default_about)

                howto_calc = ""
                if "calculator" in slug or cat_name == "Calculators":
                    howto_calc = (
                        f"<p>The {name} uses standard mathematical formulas to compute results based on your inputs. "
                        f"Enter your values, click calculate, and the tool processes everything instantly using optimized algorithms — all within your browser.</p>"
                    )

                related_slugs = [
                    t2["url"].split("/tool/")[-1]
                    for t2 in tools
                    if t2["url"].split("/tool/")[-1] != slug
                ][:6]

                date_modified = ""
                tmpl_path = os.path.join(self.settings.TEMPLATES_DIR, "tools", f"{slug.replace('-', '_')}.html")
                try:
                    mtime = os.path.getmtime(tmpl_path)
                    date_modified = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
                except OSError:
                    pass

                result[slug] = ToolSEO(
                    slug=slug,
                    name=name,
                    icon=icon,
                    description=desc,
                    keywords=keywords,
                    app_category=app_category,
                    faqs=faqs,
                    howto_steps=howto,
                    howto_calculate=howto_calc,
                    about_title=about_title,
                    about_body=about_body,
                    date_modified=date_modified,
                    related_slugs=related_slugs,
                )

        self._cat_cache = (time.time(), result)
        return result

    def get_seo(self, slug: str) -> ToolSEO | None:
        all_data = self._build_all()
        seo = all_data.get(slug)
        if seo is None:
            return None
        related = self.get_related(slug)
        seo.related = related
        return seo

    def get_related(self, slug: str) -> list[dict]:
        categories, _ = self._catalog.get_categorized_tools()
        for cat_name, tools in categories.items():
            slugs = [t["url"].split("/tool/")[-1] for t in tools]
            if slug in slugs:
                return [t for t in tools if t["url"].split("/tool/")[-1] != slug][:6]
        return []
