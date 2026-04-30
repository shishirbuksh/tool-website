import re

with open(r'e:\ruff1\tool\templates\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix Title and Meta
content = content.replace(
    '{% block title %}Free AI Tools & Utilities Online | StoryBrain AI{% endblock %}',
    '{% block title %}Free Crypto & AI Tools Online - StoryBrain AI{% endblock %}'
)
content = content.replace(
    '{% block meta_description %}Access a suite of free, fast, and secure online AI tools and calculators. No signup required.{% endblock %}',
    '{% block meta_description %}Free online AI tools for crypto price prediction, NFT generation, image editing, and more. No signup needed. Runs in your browser.{% endblock %}'
)

# Fix H1
content = re.sub(
    r'<h1 class="hero-title">\s*THE ULTIMATE <span class="gradient-text">FREE AI TOOLS</span> SUITE\s*</h1>',
    r'<h1 class="hero-title">\n        STORYBRAIN AI <span class="gradient-text">TOOLS SUITE</span>\n    </h1>',
    content
)

# Fix duplicate texts
duplicates = [
    ("Crypto Crypto Trend Analyzer", "Crypto Trend Analyzer"),
    ("Crypto Crypto Profit Calculator", "Crypto Profit Calculator"),
    ("Crypto Password Generator Generator", "Crypto Password Generator"),
    ("Crypto Crypto Mining Calculator", "Crypto Mining Calculator"),
    ("Crypto Crypto DCA Calculator", "Crypto DCA Calculator"),
    ("Crypto Crypto Price Converter", "Crypto Price Converter"),
    ("Crypto Crypto Scam Checker", "Crypto Scam Checker"),
    ("Crypto Crypto Wallet Tracker", "Crypto Wallet Tracker"),
    ("Crypto Crypto Airdrop Finder", "Crypto Airdrop Finder"),
    ("Crypto Crypto Halving Countdown", "Crypto Halving Countdown"),
    ("Image Image Background Remover", "Image Background Remover"),
    ("Scientific Calculator Calculator", "Scientific Calculator"),
    ("Standard Calculator Calculator", "Standard Calculator"),
    ("Percentage Calculator Calculator", "Percentage Calculator")
]

for old, new in duplicates:
    content = content.replace(old, new)

with open(r'e:\ruff1\tool\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html fixed!")
