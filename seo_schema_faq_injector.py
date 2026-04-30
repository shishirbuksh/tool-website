import os
import glob
import re
import json

tools_dir = r"e:\ruff1\tool\templates\tools"

tools_mapping = {
    "age_calculator.html": ("Age Calculator", "calculate your exact age"),
    "airdrop_finder.html": ("Crypto Airdrop Finder", "find the latest crypto airdrops"),
    "base64_tool.html": ("Base64 Encoder", "encode and decode Base64 strings"),
    "calculator.html": ("Standard Calculator", "perform basic math calculations"),
    "crypto_dca_calculator.html": ("Crypto DCA Calculator", "calculate Dollar Cost Averaging strategies"),
    "crypto_fear_greed_index_tracker.html": ("Fear and Greed Index", "track cryptocurrency market sentiment"),
    "crypto_halving_countdown.html": ("Crypto Halving Countdown", "track the countdown to the next halving"),
    "crypto_mining_calculator.html": ("Crypto Mining Calculator", "calculate cryptocurrency mining profitability"),
    "crypto_password_generator.html": ("Crypto Password Generator", "generate secure cryptocurrency passwords"),
    "crypto_price_converter.html": ("Crypto Price Converter", "convert cryptocurrency prices to fiat"),
    "crypto_price_prediction.html": ("Crypto Price Predictor", "predict future cryptocurrency prices"),
    "crypto_profit_calculator.html": ("Crypto Profit Calculator", "calculate cryptocurrency trading profits"),
    "crypto_scam_checker.html": ("Crypto Scam Checker", "check for cryptocurrency scams and honeypots"),
    "crypto_tax_calculator.html": ("Crypto Tax Calculator", "calculate cryptocurrency taxes"),
    "crypto_trend_analyzer.html": ("Crypto Trend Analyzer", "analyze cryptocurrency market trends"),
    "image_background_remover.html": ("Image Background Remover", "remove backgrounds from images"),
    "image_compressor.html": ("Image Compressor", "compress image file sizes"),
    "image_converter.html": ("Image Converter", "convert between different image formats"),
    "meme_coin_detector.html": ("Meme Coin Detector", "analyze and detect new meme coins"),
    "nft_generator_ai.html": ("AI NFT Generator", "generate custom AI NFT art"),
    "password_generator.html": ("Secure Password Generator", "generate highly secure passwords"),
    "pdf_converter.html": ("Free PDF Converter", "convert to and from PDF files"),
    "percentage_calculator.html": ("Percentage Calculator", "calculate percentages, margins, and growth"),
    "qr_generator.html": ("QR Code Generator", "create custom QR codes"),
    "scientific_calculator.html": ("Scientific Calculator", "perform advanced mathematical calculations"),
    "text_case_converter.html": ("Text Case Converter", "convert text to uppercase, lowercase, and more"),
    "wallet_address_tracker.html": ("Crypto Wallet Tracker", "track multiple cryptocurrency wallet balances"),
    "watermark_remover.html": ("Watermark Remover", "remove watermarks from images")
}

for filepath in glob.glob(os.path.join(tools_dir, "*.html")):
    filename = os.path.basename(filepath)
    if filename not in tools_mapping:
        continue
        
    tool_name, action = tools_mapping[filename]
    tool_url = f"https://storybrainai.com/tool/{filename[:-5].replace('_', '-')}"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if already injected
    if 'SoftwareApplication' in content or 'FAQPage' in content:
        print(f"Skipping {filename}, already has schema.")
        continue

    # 1. Generate Schema
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": tool_name,
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web browser",
                "offers": {
                    "@type": "Offer",
                    "price": "0",
                    "priceCurrency": "USD"
                },
                "description": f"Use the free {tool_name} online to {action}. No sign-up required."
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f"Is the {tool_name} free to use?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": f"Yes, our {tool_name} is completely free to use. There are no hidden fees or subscriptions required."
                        }
                    },
                    {
                        "@type": "Question",
                        "name": f"Do I need to sign up to use the {tool_name}?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "No sign-up or registration is required. You can use the tool instantly directly from your browser."
                        }
                    },
                    {
                        "@type": "Question",
                        "name": f"Is my data secure when using the {tool_name}?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Absolutely. All processing happens locally in your browser or through secure encrypted channels, ensuring your data remains private and is never stored on our servers."
                        }
                    }
                ]
            }
        ]
    }
    schema_script = f'\n<script type="application/ld+json">\n{json.dumps(schema, indent=4)}\n</script>\n'

    # 2. Generate FAQ HTML
    faq_html = f"""
<!-- FAQ Section for SEO -->
<div class="mt-5 pt-5 border-top border-theme reveal" style="animation-delay: 0.4s;">
    <h2 class="fs-3 fw-bold mb-4">Frequently Asked Questions</h2>
    <div class="accordion accordion-flush" id="faqAccordion">
        <div class="accordion-item bg-transparent border-white border-opacity-10">
            <h3 class="accordion-header">
                <button class="accordion-button collapsed bg-transparent text-theme fw-bold shadow-none" type="button" data-bs-toggle="collapse" data-bs-target="#faq1">
                    Is the {tool_name} free to use?
                </button>
            </h3>
            <div id="faq1" class="accordion-collapse collapse" data-bs-parent="#faqAccordion">
                <div class="accordion-body text-theme-muted">
                    Yes, our {tool_name} is completely free to use. There are no hidden fees or subscriptions required. StoryBrain AI provides these premium utilities at no cost to help accelerate your workflow.
                </div>
            </div>
        </div>
        <div class="accordion-item bg-transparent border-white border-opacity-10">
            <h3 class="accordion-header">
                <button class="accordion-button collapsed bg-transparent text-theme fw-bold shadow-none" type="button" data-bs-toggle="collapse" data-bs-target="#faq2">
                    Do I need to sign up to use the {tool_name}?
                </button>
            </h3>
            <div id="faq2" class="accordion-collapse collapse" data-bs-parent="#faqAccordion">
                <div class="accordion-body text-theme-muted">
                    No sign-up or registration is required. You can use the {tool_name} instantly directly from your browser without providing any personal information or creating an account.
                </div>
            </div>
        </div>
        <div class="accordion-item bg-transparent border-white border-opacity-10 border-bottom-0">
            <h3 class="accordion-header">
                <button class="accordion-button collapsed bg-transparent text-theme fw-bold shadow-none" type="button" data-bs-toggle="collapse" data-bs-target="#faq3">
                    Is my data secure when using the {tool_name}?
                </button>
            </h3>
            <div id="faq3" class="accordion-collapse collapse" data-bs-parent="#faqAccordion">
                <div class="accordion-body text-theme-muted">
                    Absolutely. All processing happens locally in your browser or through secure encrypted channels, ensuring your data remains private. We do not store or log your queries on our servers.
                </div>
            </div>
        </div>
    </div>
</div>
"""

    # Inject into the content right before {% endblock %}
    # Split the content to find the last {% endblock %}
    parts = content.rsplit('{% endblock %}', 1)
    if len(parts) == 2:
        new_content = parts[0] + faq_html + schema_script + '\n{% endblock %}' + parts[1]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filename}")
    else:
        print(f"Could not find {{% endblock %}} in {filename}")

print("All tools updated with Schema and FAQs.")
