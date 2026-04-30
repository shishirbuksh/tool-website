import os
import re
import glob

# Mapping of file to its simplified name
tools = {
    "age_calculator.html": "Age Calculator",
    "airdrop_finder.html": "Crypto Airdrop Finder",
    "base64_tool.html": "Base64 Encoder Decoder",
    "calculator.html": "Standard Calculator",
    "crypto_dca_calculator.html": "Crypto DCA Calculator",
    "crypto_fear_greed_index_tracker.html": "Crypto Fear and Greed Index",
    "crypto_halving_countdown.html": "Crypto Halving Countdown",
    "crypto_mining_calculator.html": "Crypto Mining Calculator",
    "crypto_password_generator.html": "Crypto Password Generator",
    "crypto_price_converter.html": "Crypto Price Converter",
    "crypto_price_prediction.html": "Crypto Price Predictor",
    "crypto_profit_calculator.html": "Crypto Profit Calculator",
    "crypto_scam_checker.html": "Crypto Scam Checker",
    "crypto_tax_calculator.html": "Crypto Tax Calculator",
    "crypto_trend_analyzer.html": "Crypto Trend Analyzer",
    "image_background_remover.html": "Image Background Remover",
    "image_compressor.html": "Image Compressor",
    "image_converter.html": "Image Converter",
    "meme_coin_detector.html": "Meme Coin Detector",
    "nft_generator_ai.html": "AI NFT Generator",
    "password_generator.html": "Secure Password Generator",
    "pdf_converter.html": "PDF Converter",
    "percentage_calculator.html": "Percentage Calculator",
    "qr_generator.html": "QR Code Generator",
    "scientific_calculator.html": "Scientific Calculator",
    "text_case_converter.html": "Text Case Converter",
    "wallet_address_tracker.html": "Crypto Wallet Tracker",
    "watermark_remover.html": "Watermark Remover"
}

seo_titles = {k: f"Free {v} Online | StoryBrain AI" for k, v in tools.items()}
seo_descriptions = {k: f"Use our free online {v} tool. Fast, secure, and private. Try the best {v.lower()} today with no sign-up required." for k, v in tools.items()}
seo_h1 = {k: f"FREE {v.upper().split()[0]} <span class=\"gradient-text italic\">{' '.join(v.upper().split()[1:])}</span>" if len(v.split()) > 1 else f"FREE <span class=\"gradient-text italic\">{v.upper()}</span>" for k, v in tools.items()}
seo_subtitle = {k: f"Our free online {v.lower()} is fast, secure, and easy to use. Get instant results right in your browser." for k, v in tools.items()}

tools_dir = r"e:\ruff1\tool\templates\tools"

for filename in os.listdir(tools_dir):
    if filename not in tools:
        continue
    filepath = os.path.join(tools_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace Title
    content = re.sub(
        r'{%\s*block\s+title\s*%}.*?{%\s*endblock\s*%}',
        f'{{% block title %}}{seo_titles[filename]}{{% endblock %}}',
        content,
        flags=re.DOTALL
    )

    # Replace Meta Description
    content = re.sub(
        r'{%\s*block\s+meta_description\s*%}.*?{%\s*endblock\s*%}',
        f'{{% block meta_description %}}{seo_descriptions[filename]}{{% endblock %}}',
        content,
        flags=re.DOTALL
    )

    # Replace H1
    content = re.sub(
        r'<h1[^>]*>.*?</h1>',
        f'<h1 class="display-3 fw-black mb-3 text-center">{seo_h1[filename]}</h1>',
        content,
        flags=re.DOTALL,
        count=1
    )

    # Replace Subtitle (p tag right after h1)
    # The subtitle usually has class="text-white-50 fs-5 mx-auto"
    content = re.sub(
        r'<p class="text-white-50 fs-5 mx-auto"[^>]*>.*?</p>',
        f'<p class="text-white-50 fs-5 mx-auto text-center" style="max-width: 700px;">\n        {seo_subtitle[filename]}\n    </p>',
        content,
        flags=re.DOTALL,
        count=1
    )

    # Replace SEO About Heading
    content = re.sub(
        r'<h2 class="fs-3 fw-bold mb-4">About.*?</h2>',
        f'<h2 class="fs-3 fw-bold mb-4">About the Free {tools[filename]} Tool</h2>',
        content,
        flags=re.DOTALL,
        count=1
    )

    # General SEO cleanup in SEO section headings (h3)
    # Replaces some complex words with simpler ones (just a quick pass)
    content = content.replace("Neural Segmentation", "AI Technology")
    content = content.replace("Semantic segmentation", "AI processing")
    content = content.replace("Alpha Synthesis", "High Quality Results")
    content = content.replace("Procedural art engine", "AI Art Maker")
    content = content.replace("Zero latency", "Fast processing")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done updating tool templates!")
