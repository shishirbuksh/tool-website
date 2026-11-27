ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/gif"}
MAX_IMAGE_PIXELS = 50_000_000

QUARANTINED_TOOLS: frozenset[str] = frozenset({
    "love-calculator",
    "crypto-price-prediction",
    "meme-coin-detector",
    "airdrop-finder",
    "crypto-scam-checker",
    "crypto-red-flag-self-assessment-tool",
})

QUARANTINED_BLOG_POSTS: frozenset[str] = frozenset({
    "love-calculator-explained-fun",
    "crypto-price-prediction-how-it-works",
    "meme-coin-detector-guide",
    "meme-coin-red-flags-learn-guide",
    "airdrop-finder-guide",
})

__all__ = [
    "ALLOWED_IMAGE_MIMES",
    "MAX_IMAGE_PIXELS",
    "QUARANTINED_TOOLS",
    "QUARANTINED_BLOG_POSTS",
]
