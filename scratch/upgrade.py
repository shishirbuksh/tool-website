import os
import glob

TOOLS_DIR = r"e:\ruff1\tool\templates\tools"

seo_content_mapping = {
    "age_calculator.html": ("Age Tracker & Calculator", "Chronological calculations made precise. Calculate age in years, months, and days instantly.", "Date Mathematics", "Time Analysis"),
    "base64_tool.html": ("Base64 Encode/Decode Terminal", "Rapidly encode or decode strings and files into raw Base64 logic arrays.", "Data Encoding", "Binary Transformation"),
    "calculator.html": ("Standard Matrix Calculator", "A minimalist, beautiful, and highly responsive daily arithmetic calculator.", "Basic Arithmetic", "Responsive Math"),
    "crypto_fear_greed_index_tracker.html": ("Crypto Fear & Greed Index", "Track live emotional metrics and market sentiment to perfectly time your entries and exits.", "Market Sentiment", "Live Indicators"),
    "crypto_price_prediction.html": ("AI Crypto Price Predictor", "Advanced neural forecasts and market trajectory analysis powered by ensemble AI models.", "Machine Learning", "Trend Forecasting"),
    "crypto_profit_calculator.html": ("Crypto Profit & Loss Calculator", "Complex margin, leverage, and spot ROI calculations rendered beautifully.", "Leverage Math", "ROI Tracking"),
    "crypto_tax_calculator.html": ("Crypto Tax Compliance Engine", "Multi-jurisdiction capital gains compliance calculator for the modern trader.", "Capital Gains", "Tax Strategy"),
    "crypto_trend_analyzer.html": ("Crypto Trend Sentiment Analyzer", "Real-time sentiment parsing and momentum scoring using DeepSeek linguistic logic.", "Momentum AI", "Pattern Recognition"),
    "image_background_remover.html": ("AI Background Extraction Lab", "Semantic segmentation to extract subjects and deploy transparent backgrounds instantly.", "Neural Masking", "Alpha Synthesis"),
    "image_compressor.html": ("Lossless Lens Compressor", "Studio-grade visual optimization reducing size with absolute zero quality loss.", "WebP Optimization", "Bandwidth Saving"),
    "image_converter.html": ("Universal Image Format Converter", "Flawlessly convert imagery between WEBP, PNG, JPG, and AVIF encodings.", "Format Bridging", "Asset Preparation"),
    "nft_generator_ai.html": ("AI NFT Generation Lab", "Procedural art studio powered by hybrid Rust-Python orchestration to turn prompts into assets.", "Procedural Art", "Latent Space"),
    "password_generator.html": ("Military-Grade Vault Keypad", "Cryptographic password generation with entropy scoring to secure your digital footprint.", "Entropy Scoring", "Brute-force Defense"),
    "pdf_converter.html": ("PDF Document Matrix", "Compile, convert, and manage document formats seamlessly within your browser.", "Format Assembly", "Document Control"),
    "percentage_calculator.html": ("Percentage Margin Calculator", "Margin, growth, and difference solvers for rapid financial arithmetic.", "Growth Math", "Margin Analysis"),
    "qr_generator.html": ("QR Synthesis Engine", "Generate vectorized and scannable QR matrices customized to your brand specs.", "Vector Matrix", "Quick Response"),
    "scientific_calculator.html": ("Scientific Equation Calculator", "Advanced trigonometry, logarithms, and exponents for complex engineering mathematics.", "Complex Equations", "Trigonometry"),
    "text_case_converter.html": ("Text Syntax Morph Tool", "Transform raw text into upper, lower, camel, snake, or pascal case flawlessly.", "String Manipulation", "Syntax Formatting"),
    "watermark_remover.html": ("Canvas Purifier & Inpainting", "Intelligent inpainting algorithms to remove watermarks and stray artifacts seamlessly.", "Inpainting Tech", "Canvas Restoration")
}

def generate_seo_block(filename):
    if filename not in seo_content_mapping:
        return ""
    
    title, desc, f1, f2 = seo_content_mapping[filename]
    return f"""
<!-- SEO Content Section -->
<div class="mt-5 pt-5 border-top border-theme reveal" style="animation-delay: 0.3s;">
    <h2 class="fs-3 fw-bold mb-4">About the {title}</h2>
    <div class="row g-4 text-start">
        <div class="col-md-6">
            <h3 class="fs-5 fw-bold text-theme"><i class="fa-solid fa-bolt text-primary me-2"></i> High Performance</h3>
            <p class="text-theme-muted">{desc}</p>
        </div>
        <div class="col-md-6">
            <h3 class="fs-5 fw-bold text-theme"><i class="fa-solid fa-shield-halved text-primary me-2"></i> Secure & Private</h3>
            <p class="text-theme-muted">Engineered by StoryBrain AI to ensure your data remains completely private. Zero server-side logging for total peace of mind.</p>
        </div>
        <div class="col-md-6">
            <h3 class="fs-5 fw-bold text-theme"><i class="fa-solid fa-layer-group text-primary me-2"></i> {f1}</h3>
            <p class="text-theme-muted">Optimized specifically for high-speed {f1.lower()} natively in your browser using modern Web APIs.</p>
        </div>
        <div class="col-md-6">
            <h3 class="fs-5 fw-bold text-theme"><i class="fa-solid fa-microchip text-primary me-2"></i> {f2}</h3>
            <p class="text-theme-muted">Leveraging advanced techniques in {f2.lower()} to deliver precision results every single time.</p>
        </div>
    </div>
</div>
"""

css_block = """
    /* Mobile Responsive Injection */
    @media (max-width: 768px) {
        .display-3, .display-4, .hero-title { font-size: 2.25rem !important; }
        .glass-card { padding: 1.5rem !important; }
        .row.g-4 { gap: 1rem !important; }
        .metrics-grid, .grid-layout { grid-template-columns: 1fr !important; }
    }
"""

files = glob.glob(os.path.join(TOOLS_DIR, "*.html"))
for filepath in files:
    filename = os.path.basename(filepath)
    if filename == "crypto_password_generator.html":
        continue
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    updated = False
    
    # 1. Inject CSS if not present
    if "/* Mobile Responsive Injection */" not in content and "@media (max-width: 768px)" not in content:
        # find the end of <style>
        if "</style>" in content:
            content = content.replace("</style>", css_block + "</style>")
            updated = True
            
    # 2. Inject SEO Block if not present
    if "<!-- SEO Content Section -->" not in content:
        seo_html = generate_seo_block(filename)
        if seo_html:
            # We want to inject it safely within the <main> or container block.
            # Most tools end with:
            #     </div>
            # </div>
            # {% endblock %}
            # Let's replace the last "{% endblock %}"
            
            # split by rsplit to replace only the last occurrence
            parts = content.rsplit("{% endblock %}", 1)
            if len(parts) == 2:
                content = parts[0] + seo_html + "\n{% endblock %}"
                updated = True
            
    if updated:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {filename}")
