"""i18n core: supported locales, URL helpers, hreflang matrix, UI strings.

Subdirectory strategy (SEO equity preserving):
  en (default, no prefix): /tool/emi-calculator, /blog/calculators/emi-guide
  hi/es/fr/de (prefixed):  /hi/tool/emi-calculator, /es/tool/..., /fr/tool/..., /de/tool/...

Slugs stay English (no translated slugs in v1) to avoid 301 equity loss.
"""

from __future__ import annotations

SUPPORTED_LOCALES: tuple[str, ...] = ("en", "hi", "es", "fr", "de")
DEFAULT_LOCALE = "en"

LOCALE_META: dict[str, dict[str, str]] = {
    "en": {"og_locale": "en_US", "name": "English", "html_lang": "en"},
    "hi": {"og_locale": "hi_IN", "name": "हिन्दी", "html_lang": "hi"},
    "es": {"og_locale": "es_ES", "name": "Español", "html_lang": "es"},
    "fr": {"og_locale": "fr_FR", "name": "Français", "html_lang": "fr"},
    "de": {"og_locale": "de_DE", "name": "Deutsch", "html_lang": "de"},
}

_LOCALE_SET = set(SUPPORTED_LOCALES)


def is_supported_locale(value: str | None) -> bool:
    return bool(value) and value.strip().lower() in _LOCALE_SET


def normalize_locale(value: str | None) -> str:
    v = (value or "").strip().lower()
    return v if v in _LOCALE_SET else DEFAULT_LOCALE


def split_locale_path(path: str) -> tuple[str, str]:
    """Split '/hi/tool/x' -> ('hi', '/tool/x'); '/tool/x' -> ('en', '/tool/x')."""
    if not path.startswith("/"):
        path = "/" + path
    parts = path.split("/", 2)
    # parts[0]='', parts[1]=candidate, parts[2]=rest
    if len(parts) >= 2 and parts[1].lower() in _LOCALE_SET and parts[1].lower() != DEFAULT_LOCALE:
        rest = "/" + parts[2] if len(parts) > 2 else "/"
        return parts[1].lower(), rest
    return DEFAULT_LOCALE, path


def localize_path(path: str, locale: str) -> str:
    """Prefix non-default locale: '/tool/x'+'hi' -> '/hi/tool/x'. Idempotent."""
    locale = normalize_locale(locale)
    _, bare = split_locale_path(path)
    if locale == DEFAULT_LOCALE:
        return bare
    if bare == "/":
        return f"/{locale}/"
    return f"/{locale}{bare}"


def localize_url(site_url: str, path: str, locale: str) -> str:
    return site_url.rstrip("/") + localize_path(path, locale)


def hreflang_links(site_url: str, bare_path: str) -> list[dict[str, str]]:
    """Full hreflang cluster for a bare (EN) path, incl. x-default -> EN."""
    base = site_url.rstrip("/")
    _, bare = split_locale_path(bare_path)
    links: list[dict[str, str]] = []
    for loc in SUPPORTED_LOCALES:
        links.append({"hreflang": loc, "href": base + localize_path(bare, loc)})
    links.append({"hreflang": "x-default", "href": base + localize_path(bare, DEFAULT_LOCALE)})
    return links


def og_locale_for(locale: str) -> str:
    return LOCALE_META.get(normalize_locale(locale), LOCALE_META["en"])["og_locale"]


def html_lang_for(locale: str) -> str:
    return LOCALE_META.get(normalize_locale(locale), LOCALE_META["en"])["html_lang"]


# ---------------------------------------------------------------------------
# UI chrome strings (human-reviewed v1). Tool bodies stay EN except locales
# whose YAML carries i18n.* overrides. Extend per locale over time.
# ---------------------------------------------------------------------------
UI_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav.home": "Home",
        "nav.tools": "Tools",
        "nav.blog": "Blog",
        "nav.all_tools": "All Tools",
        "search.title": "Search Tools",
        "search.placeholder": "Type to search 117+ tools...",
        "search.empty": "Start typing to find tools",
        "cookie.title": "Privacy & Cookies",
        "cookie.accept": "Accept All",
        "cookie.reject": "Reject",
        "breadcrumb.home": "Home",
        "breadcrumb.tools": "Tools",
        "footer.tagline": "Built for speed & privacy.",
        "footer.popular": "Popular Tools",
        "footer.categories": "Categories",
        "footer.legal": "Legal",
        "cookie.body": "We use cookies to improve your experience and analyze traffic.",
        "cookie.privacy": "Read our Privacy Policy",
        "blog.title": "Blog",
        "nav.about": "About",
        "nav.contact": "Contact",
        "nav.search": "Search",
        "nav.theme": "Theme",
        "nav.menu": "Menu",
        "nav.language": "Language",
        "nav.categories": "Categories",
    },
    "hi": {
        "nav.home": "होम",
        "nav.tools": "टूल्स",
        "nav.blog": "ब्लॉग",
        "nav.all_tools": "सभी टूल्स",
        "search.title": "टूल्स खोजें",
        "search.placeholder": "117+ टूल्स खोजने के लिए लिखें...",
        "search.empty": "टूल्स खोजने के लिए लिखना शुरू करें",
        "cookie.title": "गोपनीयता और कुकीज़",
        "cookie.accept": "सभी स्वीकार करें",
        "cookie.reject": "अस्वीकार करें",
        "breadcrumb.home": "होम",
        "breadcrumb.tools": "टूल्स",
        "footer.tagline": "गति और गोपनीयता के लिए निर्मित।",
        "footer.popular": "लोकप्रिय टूल्स",
        "footer.categories": "श्रेणियां",
        "footer.legal": "कानूनी",
        "cookie.body": "हम आपके अनुभव को बेहतर बनाने और ट्रैफ़िक का विश्लेषण करने के लिए कुकीज़ का उपयोग करते हैं।",
        "cookie.privacy": "हमारी गोपनीयता नीति पढ़ें",
        "blog.title": "ब्लॉग",
        "nav.about": "हमारे बारे में",
        "nav.contact": "संपर्क",
        "nav.search": "खोजें",
        "nav.theme": "थीम",
        "nav.menu": "मेन्यू",
        "nav.language": "भाषा",
        "nav.categories": "श्रेणियां",
    },
    "es": {
        "nav.home": "Inicio",
        "nav.tools": "Herramientas",
        "nav.blog": "Blog",
        "nav.all_tools": "Todas las herramientas",
        "search.title": "Buscar herramientas",
        "search.placeholder": "Escribe para buscar más de 117 herramientas...",
        "search.empty": "Empieza a escribir para encontrar herramientas",
        "cookie.title": "Privacidad y cookies",
        "cookie.accept": "Aceptar todo",
        "cookie.reject": "Rechazar",
        "breadcrumb.home": "Inicio",
        "breadcrumb.tools": "Herramientas",
        "footer.tagline": "Creado para velocidad y privacidad.",
        "footer.popular": "Herramientas populares",
        "footer.categories": "Categorías",
        "footer.legal": "Legal",
        "cookie.body": "Usamos cookies para mejorar tu experiencia y analizar el tráfico.",
        "cookie.privacy": "Lee nuestra política de privacidad",
        "blog.title": "Blog",
        "nav.about": "Acerca de",
        "nav.contact": "Contacto",
        "nav.search": "Buscar",
        "nav.theme": "Tema",
        "nav.menu": "Menú",
        "nav.language": "Idioma",
        "nav.categories": "Categorías",
    },
    "fr": {
        "nav.home": "Accueil",
        "nav.tools": "Outils",
        "nav.blog": "Blog",
        "nav.all_tools": "Tous les outils",
        "search.title": "Rechercher des outils",
        "search.placeholder": "Tapez pour rechercher parmi 117+ outils...",
        "search.empty": "Commencez à taper pour trouver des outils",
        "cookie.title": "Confidentialité et cookies",
        "cookie.accept": "Tout accepter",
        "cookie.reject": "Refuser",
        "breadcrumb.home": "Accueil",
        "breadcrumb.tools": "Outils",
        "footer.tagline": "Conçu pour la vitesse et la confidentialité.",
        "footer.popular": "Outils populaires",
        "footer.categories": "Catégories",
        "footer.legal": "Mentions légales",
        "cookie.body": "Nous utilisons des cookies pour améliorer votre expérience et analyser le trafic.",
        "cookie.privacy": "Lire notre politique de confidentialité",
        "blog.title": "Blog",
        "nav.about": "À propos",
        "nav.contact": "Contact",
        "nav.search": "Rechercher",
        "nav.theme": "Thème",
        "nav.menu": "Menu",
        "nav.language": "Langue",
        "nav.categories": "Catégories",
    },
    "de": {
        "nav.home": "Startseite",
        "nav.tools": "Tools",
        "nav.blog": "Blog",
        "nav.all_tools": "Alle Tools",
        "search.title": "Tools suchen",
        "search.placeholder": "117+ Tools suchen...",
        "search.empty": "Tippen Sie, um Tools zu finden",
        "cookie.title": "Datenschutz & Cookies",
        "cookie.accept": "Alle akzeptieren",
        "cookie.reject": "Ablehnen",
        "breadcrumb.home": "Startseite",
        "breadcrumb.tools": "Tools",
        "footer.tagline": "Für Speed & Privatsphäre gebaut.",
        "footer.popular": "Beliebte Tools",
        "footer.categories": "Kategorien",
        "footer.legal": "Rechtliches",
        "cookie.body": "Wir verwenden Cookies, um Ihr Erlebnis zu verbessern und Traffic zu analysieren.",
        "cookie.privacy": "Datenschutzerklärung lesen",
        "blog.title": "Blog",
        "nav.about": "Über uns",
        "nav.contact": "Kontakt",
        "nav.search": "Suchen",
        "nav.theme": "Theme",
        "nav.menu": "Menü",
        "nav.language": "Sprache",
        "nav.categories": "Kategorien",
    },
}


def t(key: str, locale: str) -> str:
    loc = normalize_locale(locale)
    table = UI_STRINGS.get(loc, UI_STRINGS["en"])
    if key in table:
        return table[key]
    return UI_STRINGS["en"].get(key, key)


# ---------------------------------------------------------------------------
# Localized taxonomy labels (hub categories + blog pillars + hub SEO titles).
# Lookup keys stay English everywhere (catalog keys, HUB_CATEGORIES, pillar
# slugs); these are display-only. Unknown locale/slug falls back to EN.
# ---------------------------------------------------------------------------
CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "hi": {
        "AI & Crypto": "AI और क्रिप्टो",
        "Calculators": "कैलकुलेटर",
        "Image Processing": "इमेज प्रोसेसिंग",
        "Developer & SEO": "डेवलपर और SEO",
        "Business & Operations": "बिज़नेस और ऑपरेशंस",
        "Productivity & Utilities": "प्रोडक्टिविटी और यूटिलिटी",
    },
    "es": {
        "AI & Crypto": "IA y Cripto",
        "Calculators": "Calculadoras",
        "Image Processing": "Procesamiento de imágenes",
        "Developer & SEO": "Desarrollo y SEO",
        "Business & Operations": "Negocios y Operaciones",
        "Productivity & Utilities": "Productividad y Utilidades",
    },
    "fr": {
        "AI & Crypto": "IA et Crypto",
        "Calculators": "Calculatrices",
        "Image Processing": "Traitement d'images",
        "Developer & SEO": "Dev et SEO",
        "Business & Operations": "Business et Opérations",
        "Productivity & Utilities": "Productivité et Utilitaires",
    },
    "de": {
        "AI & Crypto": "KI & Krypto",
        "Calculators": "Rechner",
        "Image Processing": "Bildbearbeitung",
        "Developer & SEO": "Dev & SEO",
        "Business & Operations": "Business & Betrieb",
        "Productivity & Utilities": "Produktivität & Tools",
    },
}

PILLAR_LABELS: dict[str, dict[str, str]] = {
    "hi": {
        "calculators": "कैलकुलेटर",
        "ai-crypto": "AI-क्रिप्टो",
        "business-operations": "बिज़नेस संचालन",
        "developer-seo": "डेवलपर SEO",
        "image-processing": "इमेज प्रोसेसिंग",
        "productivity-utilities": "उत्पादकता",
    },
    "es": {
        "calculators": "Calculadoras",
        "ai-crypto": "IA y Cripto",
        "business-operations": "Operaciones de negocio",
        "developer-seo": "Desarrollo y SEO",
        "image-processing": "Procesamiento de imágenes",
        "productivity-utilities": "Productividad",
    },
    "fr": {
        "calculators": "Calculatrices",
        "ai-crypto": "IA et Crypto",
        "business-operations": "Opérations business",
        "developer-seo": "Dev et SEO",
        "image-processing": "Traitement d'images",
        "productivity-utilities": "Productivité",
    },
    "de": {
        "calculators": "Rechner",
        "ai-crypto": "KI-Krypto",
        "business-operations": "Business-Betrieb",
        "developer-seo": "Dev-SEO",
        "image-processing": "Bildbearbeitung",
        "productivity-utilities": "Produktivität",
    },
}

HUB_SEO_TITLES: dict[str, dict[str, str]] = {
    "hi": {
        "ai-tools": "AI और क्रिप्टो टूल्स — मुफ्त ऑनलाइन",
        "calculators": "मुफ्त कैलकुलेटर — EMI, SIP, FD",
        "image-tools": "मुफ्त इमेज टूल्स — ऑनलाइन",
        "developer-tools": "डेवलपर और SEO टूल्स मुफ्त",
        "business-tools": "बिज़नेस टूल्स — इनवॉइस, GST",
        "productivity-tools": "PDF व उत्पादकता टूल्स मुफ्त",
        "pdf-tools": "PDF व उत्पादकता टूल्स मुफ्त",
    },
    "es": {
        "ai-tools": "Herramientas IA y Cripto gratis",
        "calculators": "Calculadoras gratis — EMI, SIP",
        "image-tools": "Herramientas de imagen gratis",
        "developer-tools": "Herramientas SEO y dev gratis",
        "business-tools": "Herramientas de negocio gratis",
        "productivity-tools": "PDF y productividad gratis",
        "pdf-tools": "PDF y productividad gratis",
    },
    "fr": {
        "ai-tools": "Outils IA et Crypto gratuits",
        "calculators": "Calculatrices gratuites en ligne",
        "image-tools": "Outils image gratuits en ligne",
        "developer-tools": "Outils dev et SEO gratuits",
        "business-tools": "Outils business gratuits",
        "productivity-tools": "PDF et productivité gratuits",
        "pdf-tools": "PDF et productivité gratuits",
    },
    "de": {
        "ai-tools": "KI- und Krypto-Tools – kostenlos online",
        "calculators": "Kostenlose Rechner – EMI, SIP, FD",
        "image-tools": "Kostenlose Bild-Tools – online",
        "developer-tools": "Dev- und SEO-Tools kostenlos",
        "business-tools": "Business-Tools – Rechnung, GST",
        "productivity-tools": "PDF- & Produktivitäts-Tools gratis",
        "pdf-tools": "PDF- & Produktivitäts-Tools gratis",
    },
}


def category_label(name: str, locale: str) -> str:
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return name
    return CATEGORY_LABELS.get(loc, {}).get(name, name)


def pillar_label(pillar: str, locale: str) -> str:
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return pillar.replace("-", " ").title()
    return PILLAR_LABELS.get(loc, {}).get(pillar, pillar.replace("-", " ").title())


def hub_seo_title(hub: str, locale: str, fallback: str = "") -> str:
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return fallback
    return HUB_SEO_TITLES.get(loc, {}).get(hub, fallback)
