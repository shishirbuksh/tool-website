"""i18n core: supported locales, URL helpers, hreflang matrix, UI strings.

Subdirectory strategy (SEO equity preserving):
  en (default, no prefix): /tool/emi-calculator, /blog/calculators/emi-guide
  hi/es/fr (prefixed):     /hi/tool/emi-calculator, /es/tool/..., /fr/tool/...

Slugs stay English (no translated slugs in v1) to avoid 301 equity loss.
"""

from __future__ import annotations

SUPPORTED_LOCALES: tuple[str, ...] = ("en", "hi", "es", "fr")
DEFAULT_LOCALE = "en"

LOCALE_META: dict[str, dict[str, str]] = {
    "en": {"og_locale": "en_US", "name": "English", "html_lang": "en"},
    "hi": {"og_locale": "hi_IN", "name": "हिन्दी", "html_lang": "hi"},
    "es": {"og_locale": "es_ES", "name": "Español", "html_lang": "es"},
    "fr": {"og_locale": "fr_FR", "name": "Français", "html_lang": "fr"},
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
# UI chrome strings (human-reviewed v1). Tool bodies stay EN except HI pilot
# tools whose YAML carries i18n.* overrides. Extend per locale over time.
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
    },
}


def t(key: str, locale: str) -> str:
    loc = normalize_locale(locale)
    table = UI_STRINGS.get(loc, UI_STRINGS["en"])
    if key in table:
        return table[key]
    return UI_STRINGS["en"].get(key, key)
