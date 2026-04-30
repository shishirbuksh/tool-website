import re

with open(r'e:\ruff1\tool\templates\base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Navbar Replacements
nav_replacements = [
    # Engines
    (r'Crypto Predictor<span class="desc">Neural market forecasting</span>', 'Crypto Price Predictor<span class="desc">Forecast future prices</span>'),
    (r'Trend Analyzer<span class="desc">Market sentiment AI</span>', 'Crypto Trend Analyzer<span class="desc">Analyze market sentiment</span>'),
    (r'NFT Lab<span class="desc">Procedural art engine</span>', 'AI NFT Generator<span class="desc">Create custom NFT art</span>'),
    (r'Fear/Greed Index<span class="desc">Real-time emotion tracker</span>', 'Fear & Greed Index<span class="desc">Track market emotions</span>'),
    (r'Profit Calc<span class="desc">ROI and leverage math</span>', 'Profit Calculator<span class="desc">Calculate crypto profits</span>'),
    (r'Tax Engine<span class="desc">Multi-region compliance</span>', 'Tax Calculator<span class="desc">Calculate crypto taxes</span>'),
    (r'Crypto Password<span class="desc">BIP39 Seed Phrases</span>', 'Password Generator<span class="desc">Generate secure passwords</span>'),
    (r'Wallet Tracker<span class="desc">Multi-chain portfolio monitor</span>', 'Wallet Tracker<span class="desc">Track crypto balances</span>'),
    (r'Meme Detector<span class="desc">Degen asset forensics</span>', 'Meme Coin Detector<span class="desc">Find safe meme coins</span>'),
    (r'Airdrop Finder<span class="desc">Sybil resistance analyzer</span>', 'Airdrop Finder<span class="desc">Find free crypto airdrops</span>'),
    (r'Halving Countdown<span class="desc">Dynamic block telemetry</span>', 'Halving Countdown<span class="desc">Track the next halving</span>'),

    # Media
    (r'BG Remover<span class="desc">Semantic segmentation</span>', 'Background Remover<span class="desc">Remove image backgrounds</span>'),
    (r'Compressor<span class="desc">Zero quality loss tech</span>', 'Image Compressor<span class="desc">Compress image size</span>'),
    (r'Format Converter<span class="desc">Universal format switching</span>', 'Image Converter<span class="desc">Convert image formats</span>'),
    (r'Canvas Purifier<span class="desc">Intelligent inpainting</span>', 'Watermark Remover<span class="desc">Remove watermarks easily</span>'),

    # Utilities
    (r'Vault Keypad<span class="desc">Military-grade generator</span>', 'Secure Password<span class="desc">Generate secure passwords</span>'),
    (r'PDF Matrix<span class="desc">Format management</span>', 'Free PDF Converter<span class="desc">Convert to/from PDF</span>'),
    (r'QR Synthesis<span class="desc">Vectorized matricies</span>', 'QR Code Generator<span class="desc">Create custom QR codes</span>'),
    (r'Base64 Terminal<span class="desc">Raw logic arrays</span>', 'Base64 Encoder<span class="desc">Encode/decode Base64</span>'),
    (r'Text Morph<span class="desc">Multi-case transformer</span>', 'Text Case Converter<span class="desc">Change text casing</span>'),

    # Math
    (r'Scientific Calc<span class="desc">Complex equations</span>', 'Scientific Calculator<span class="desc">Solve complex math</span>'),
    (r'Standard Calc<span class="desc">Minimal arithmetic</span>', 'Standard Calculator<span class="desc">Free online calculator</span>'),
    (r'Percentage Calc<span class="desc">Margin & growth solvers</span>', 'Percentage Calculator<span class="desc">Calculate percentages</span>'),
    (r'Age Tracker<span class="desc">Chronological maths</span>', 'Age Calculator<span class="desc">Calculate exact age</span>')
]

for old, new in nav_replacements:
    content = content.replace(old, new)

# 2. Sidebar Replacements
sidebar_replacements = [
    # AI & Engines
    (r'<i class="fa-solid fa-chart-line text-theme-muted me-2 w-1w"></i> Crypto Predictor', '<i class="fa-solid fa-chart-line text-theme-muted me-2 w-1w"></i> Crypto Price Predictor'),
    (r'<i class="fa-solid fa-brain text-theme-muted me-2 w-1w"></i> Trend Analyzer', '<i class="fa-solid fa-brain text-theme-muted me-2 w-1w"></i> Crypto Trend Analyzer'),
    (r'<i class="fa-solid fa-palette text-theme-muted me-2 w-1w"></i> AI NFT Lab', '<i class="fa-solid fa-palette text-theme-muted me-2 w-1w"></i> Free AI NFT Generator'),
    (r'<i class="fa-solid fa-gauge-high text-theme-muted me-2 w-1w"></i> Fear & Greed Tracker', '<i class="fa-solid fa-gauge-high text-theme-muted me-2 w-1w"></i> Fear & Greed Index'),
    (r'<i class="fa-solid fa-coins text-theme-muted me-2 w-1w"></i> Profit Calculator', '<i class="fa-solid fa-coins text-theme-muted me-2 w-1w"></i> Crypto Profit Calculator'),
    (r'<i class="fa-solid fa-file-invoice-dollar text-theme-muted me-2 w-1w"></i> Tax Engine', '<i class="fa-solid fa-file-invoice-dollar text-theme-muted me-2 w-1w"></i> Crypto Tax Calculator'),
    (r'<i class="fa-solid fa-shield-halved text-theme-muted me-2 w-1w"></i> Crypto Password', '<i class="fa-solid fa-shield-halved text-theme-muted me-2 w-1w"></i> Crypto Passwords'),
    
    # Media Studio
    (r'<i class="fa-solid fa-user-large-slash text-theme-muted me-2 w-1w"></i> BG Remover', '<i class="fa-solid fa-user-large-slash text-theme-muted me-2 w-1w"></i> Background Remover'),
    (r'<i class="fa-solid fa-compress text-theme-muted me-2 w-1w"></i> Lens Compressor', '<i class="fa-solid fa-compress text-theme-muted me-2 w-1w"></i> Image Compressor'),
    (r'<i class="fa-solid fa-file-image text-theme-muted me-2 w-1w"></i> Format Converter', '<i class="fa-solid fa-file-image text-theme-muted me-2 w-1w"></i> Image Converter'),
    (r'<i class="fa-solid fa-eraser text-theme-muted me-2 w-1w"></i> Canvas Purifier', '<i class="fa-solid fa-eraser text-theme-muted me-2 w-1w"></i> Watermark Remover'),

    # Pro Utilities -> Utilities
    (r'Pro Utilities</h6>', 'Utilities</h6>'),
    (r'<i class="fa-solid fa-key text-theme-muted me-2 w-1w"></i> Vault Keypad', '<i class="fa-solid fa-key text-theme-muted me-2 w-1w"></i> Secure Password'),
    (r'<i class="fa-solid fa-file-pdf text-theme-muted me-2 w-1w"></i> PDF Matrix', '<i class="fa-solid fa-file-pdf text-theme-muted me-2 w-1w"></i> Free PDF Converter'),
    (r'<i class="fa-solid fa-qrcode text-theme-muted me-2 w-1w"></i> QR Synthesis', '<i class="fa-solid fa-qrcode text-theme-muted me-2 w-1w"></i> QR Code Generator'),
    (r'<i class="fa-solid fa-code text-theme-muted me-2 w-1w"></i> Base64 Terminal', '<i class="fa-solid fa-code text-theme-muted me-2 w-1w"></i> Base64 Encoder'),
    (r'<i class="fa-solid fa-font text-theme-muted me-2 w-1w"></i> Text Morph', '<i class="fa-solid fa-font text-theme-muted me-2 w-1w"></i> Text Case Converter'),

    # Mathematics
    (r'<i class="fa-solid fa-flask-vial text-theme-muted me-2 w-1w"></i> Scientific', '<i class="fa-solid fa-flask-vial text-theme-muted me-2 w-1w"></i> Scientific Calculator'),
    (r'<i class="fa-solid fa-plus-minus text-theme-muted me-2 w-1w"></i> Standard', '<i class="fa-solid fa-plus-minus text-theme-muted me-2 w-1w"></i> Standard Calculator'),
    (r'<i class="fa-solid fa-percent text-theme-muted me-2 w-1w"></i> Percentage', '<i class="fa-solid fa-percent text-theme-muted me-2 w-1w"></i> Percentage Calculator'),
    (r'<i class="fa-solid fa-calendar-days text-theme-muted me-2 w-1w"></i> Age Tracker', '<i class="fa-solid fa-calendar-days text-theme-muted me-2 w-1w"></i> Age Calculator')
]

for old, new in sidebar_replacements:
    content = content.replace(old, new)


# 3. Add legal/company pages to the sidebar
# We will inject this right before the closing div of the offcanvas-body
company_sidebar_html = """
            <!-- Company & Legal -->
            <div class="mb-4">
                <h6 class="small fw-black tracking-widest text-uppercase mb-2" style="color: var(--sb-text-muted);"><i class="fa-solid fa-building me-2 text-theme-faint"></i> Company & Legal</h6>
                <div class="list-group list-group-flush gap-1">
                    <a href="/about" class="list-group-item list-group-item-action bg-transparent border-0 px-3 py-2 rounded-3 text-theme sidebar-item"><i class="fa-solid fa-circle-info text-theme-muted me-2 w-1w"></i> About Us</a>
                    <a href="/contact" class="list-group-item list-group-item-action bg-transparent border-0 px-3 py-2 rounded-3 text-theme sidebar-item"><i class="fa-solid fa-envelope text-theme-muted me-2 w-1w"></i> Contact Us</a>
                    <a href="/privacy" class="list-group-item list-group-item-action bg-transparent border-0 px-3 py-2 rounded-3 text-theme sidebar-item"><i class="fa-solid fa-user-shield text-theme-muted me-2 w-1w"></i> Privacy Policy</a>
                    <a href="/terms" class="list-group-item list-group-item-action bg-transparent border-0 px-3 py-2 rounded-3 text-theme sidebar-item"><i class="fa-solid fa-file-contract text-theme-muted me-2 w-1w"></i> Terms of Service</a>
                    <a href="/disclaimer" class="list-group-item list-group-item-action bg-transparent border-0 px-3 py-2 rounded-3 text-theme sidebar-item"><i class="fa-solid fa-triangle-exclamation text-theme-muted me-2 w-1w"></i> Disclaimer</a>
                </div>
            </div>
            
        </div>
    </div>
"""

content = content.replace('            \n        </div>\n    </div>', company_sidebar_html)
# If the exact match fails due to spaces, we use regex
content = re.sub(r'(\s*</div>\s*</div>\s*<!-- ── Main Workspace ── -->)', r'\n' + company_sidebar_html + r'\n\1', content)

with open(r'e:\ruff1\tool\templates\base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated base.html navbar and sidebar!")
