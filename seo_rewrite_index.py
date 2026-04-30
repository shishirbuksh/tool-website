import re

with open(r'e:\ruff1\tool\templates\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Title and Meta Description
content = re.sub(
    r'{%\s*block\s+title\s*%}.*?{%\s*endblock\s*%}',
    r'{% block title %}Free AI Tools & Utilities Online | StoryBrain AI{% endblock %}',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'{%\s*block\s+meta_description\s*%}.*?{%\s*endblock\s*%}',
    r'{% block meta_description %}Access a suite of free, fast, and secure online AI tools and calculators. No signup required.{% endblock %}',
    content,
    flags=re.DOTALL
)

# 2. Update Hero H1 and Subtitle
content = re.sub(
    r'<h1 class="hero-title">.*?</h1>',
    r'<h1 class="hero-title">\n        THE ULTIMATE <span class="gradient-text">FREE AI TOOLS</span> SUITE\n    </h1>',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'<p class="hero-subtitle">.*?</p>',
    r'<p class="hero-subtitle">\n        Accelerate your workflow with an ecosystem of free online tools and calculators. Built for speed, privacy, and flawless execution right in your browser.\n    </p>',
    content,
    flags=re.DOTALL
)

# 3. Simplify Tool Cards

replacements = [
    # AI & Crypto
    (r'AI Price Predictor', 'Crypto Price Predictor'),
    (r'Advanced neural forecasts and market trajectory analysis powered by ensemble AI models\.', 'Forecast future cryptocurrency prices using advanced AI models.'),
    
    (r'Trend Analyzer', 'Crypto Trend Analyzer'),
    (r'Real-time sentiment parsing and momentum scoring using DeepSeek linguistic logic\.', 'Analyze live market sentiment to spot crypto trends early.'),
    
    (r'AI NFT Lab', 'Free AI NFT Generator'),
    (r'Generative procedural art studio\. Turn prompts into mint-ready assets instantly\.', 'Create custom NFT art instantly using our free AI generator.'),
    
    (r'Fear & Greed Index', 'Fear and Greed Index'),
    (r'Live emotional metrics of the crypto market to perfectly time your entries and exits\.', 'Track the real-time crypto market emotions to make better trading decisions.'),
    
    (r'Profit Calculator', 'Crypto Profit Calculator'),
    (r'Complex margin, leverage, and spot ROI calculations rendered beautifully\.', 'Easily calculate your crypto profit, ROI, and leverage margins.'),
    
    (r'Crypto Tax Engine', 'Crypto Tax Calculator'),
    (r'Multi-jurisdiction capital gains compliance calculator \(US, CA, IN\)\.', 'Calculate your cryptocurrency taxes quickly and accurately.'),
    
    (r'Crypto Password', 'Crypto Password Generator'),
    (r'Generate military-grade BIP39 seed phrases and high-entropy private keys locally\.', 'Generate highly secure BIP39 seed phrases and crypto private keys.'),
    
    (r'Mining Calculator', 'Crypto Mining Calculator'),
    (r'Advanced profitability metrics for Proof-of-Work hardware and networks\.', 'Check the profitability of your crypto mining hardware instantly.'),
    
    (r'DCA Calculator', 'Crypto DCA Calculator'),
    (r'Model compounding growth and optimize recurring investment schedules vs lump sum\.', 'Calculate the returns on your dollar-cost averaging crypto investments.'),
    
    (r'Price Converter', 'Crypto Price Converter'),
    (r'Real-time exchange rates across the top 100 digital assets and fiat reserves\.', 'Convert crypto prices to fiat in real-time with accurate exchange rates.'),
    
    (r'Scam Checker', 'Crypto Scam Checker'),
    (r'Deep heuristic scans on crypto addresses and contracts to detect rug pulls instantly\.', 'Check crypto tokens and contracts for scams and rug pulls instantly.'),
    
    (r'Wallet Tracker', 'Crypto Wallet Tracker'),
    (r'Institutional-grade multi-chain portfolio monitor\. Track balances and real-time net worth\.', 'Track your multi-chain crypto wallet balances in one secure dashboard.'),
    
    (r'Meme Detector', 'Meme Coin Detector'),
    (r'Analyze live liquidity, temporal inception, and linguistics to expose high-risk degen assets\.', 'Detect high-risk meme coins and analyze their liquidity instantly.'),
    
    (r'Airdrop Finder', 'Crypto Airdrop Finder'),
    (r'Discover Tier-1 un-tokenized ecosystems and analyze your wallet\'s Sybil resistance score\.', 'Find the latest free crypto airdrops and check your eligibility.'),
    
    (r'Halving Countdown', 'Crypto Halving Countdown'),
    (r'Institutional macro-economic tracking\. Calculate precise halving ETAs via live node telemetry\.', 'Track the live countdown to the next major crypto halving event.'),

    # Media Studio
    (r'Background Remover', 'Image Background Remover'),
    (r'Semantic segmentation to extract subjects and deploy transparent backgrounds\.', 'Easily remove the background from any image for free online.'),
    
    (r'Lens Compressor', 'Image Compressor'),
    (r'Studio-grade visual optimization reducing size with absolute zero quality loss\.', 'Compress image file sizes online without losing visual quality.'),
    
    (r'Universal Format', 'Image Converter'),
    (r'Flawlessly convert imagery between WEBP, PNG, JPG, and AVIF encodings\.', 'Convert images between JPG, PNG, WEBP, and AVIF formats for free.'),
    
    (r'Canvas Purifier', 'Watermark Remover'),
    (r'Intelligent inpainting algorithms to remove watermarks and stray artifacts seamlessly\.', 'Remove watermarks and unwanted objects from images instantly.'),

    # Daily Utilities
    (r'Vault Keypad', 'Secure Password Generator'),
    (r'Military-grade cryptographic password generation and entropy scoring\.', 'Generate highly secure, random passwords to protect your accounts.'),
    
    (r'PDF Matrix', 'Free PDF Converter'),
    (r'Compile, convert, and manage document formats directly in-browser seamlessly\.', 'Convert to and from PDF format easily with our free online tool.'),
    
    (r'QR Synthesis', 'QR Code Generator'),
    (r'Generate vectorized and scannable QR matrices customized to your brand specs\.', 'Create custom, high-quality QR codes for links, text, and more.'),
    
    (r'Base64 Terminal', 'Base64 Encoder / Decoder'),
    (r'Rapid encode/decode strings and files into Base64 raw logic arrays\.', 'Quickly encode or decode text and files using Base64 format.'),
    
    (r'Text Syntax Tool', 'Text Case Converter'),
    (r'Transform raw text into upper, lower, camel, or snake case flawlessly\.', 'Convert your text to uppercase, lowercase, camelCase, and more.'),

    # Mathematics
    (r'<h3 class="tool-name fs-5">Scientific', '<h3 class="tool-name fs-5">Scientific Calculator'),
    (r'Advanced trigonometry and exponents\.', 'Solve complex math problems with our free online scientific calculator.'),
    
    (r'<h3 class="tool-name fs-5">Standard', '<h3 class="tool-name fs-5">Standard Calculator'),
    (r'Beautiful minimalist daily arithmetic\.', 'A simple, fast, and free online calculator for daily math.'),
    
    (r'<h3 class="tool-name fs-5">Percentage', '<h3 class="tool-name fs-5">Percentage Calculator'),
    (r'Margin, growth, and difference solvers\.', 'Easily calculate percentages, margins, and growth for free.'),
    
    (r'<h3 class="tool-name fs-5">Age Tracker', '<h3 class="tool-name fs-5">Age Calculator'),
    (r'Chronological precise timeline maths\.', 'Calculate your exact age in years, months, and days instantly.')
]

for old, new in replacements:
    content = re.sub(old, new, content, count=1)

with open(r'e:\ruff1\tool\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated index.html!")
