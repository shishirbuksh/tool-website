# StoryBrain AI — Full Deep Audit Report

> Generated: 2026-10-05 (Build mode, verified by execution). Updated: catalog expanded 107 → 117 tools.
> Scope: full code / files / folders / functions / tools / blog / SEO / technical / security / deep audit + product expansion
> Method: `data/tools.yaml` + `data/blog.yaml` parsed with PyYAML, template grep, `TestClient` render checks, sitemap service invocation, `pytest --collect-only`, `ruff check`.

## Executive Summary

| Area | Verdict |
|---|---|
| Content integrity (tools/blog links) | **PASS** — 0 broken `related_slugs`, 0 broken blog→tool refs, 0 broken `/tool/` body links, 0 broken `related_posts`, 107/107 templates present |
| Sitemap / robots | **PASS** — 215 unique URLs, 0 duplicates, valid XML, correct disallows |
| SEO blocking issues | **NONE** — no noindex on HTML, correct canonical, CSP nonce present, 4× `ld+json` blocks per tool page as designed |
| Cleanup debt (non-blocking) | **DONE 2026-10-05: 44 `seo_schema` overrides merged; `tool_base.html` deleted; all inline handlers eliminated + CSP test tightened; 29 `meta_title` overrides + 64 descriptions fixed in YAML; 30 redundant image blocks deleted. Remaining: single shared OG image (needs design work), dead template head blocks (see §5)** |
| Perf risk | **Medium** — `app.css` 362.8 KB, vendor `apexcharts 586.7 KB + chart 203.6 KB` (lazy-loaded, OK), HTML `no-store` by design (nonce rotation) |
| Security | **PASS with 2 alignment TODOs** — CSP/HSTS/nosniff present, `/api/*` noindex, fail-closed prod config |
| Tests / lint | **201 tests collected, sample suites PASS; `ruff check app` = 78 errors (mostly SIM, fixable)** |

---

## 1. File / Folder Inventory (283 files excl. `.git/node_modules/venv/__pycache__`)

| Ext | Count | Notes |
|---|---|---|
| `.html` | 132 | `templates/`: base, tool_base, index, hub, tools/107, blog/3, pages/10, components/8 |
| `.py` | 82 | `app/` + `scripts/` + `tests/` (25 test files) + root fix_*.py (7 legacy fix scripts — candidate for removal) |
| `.js` | 14 | `src/js/3` source, `static/js/5` built + 2 vendor + `sw.js`, `scripts/2` |
| `.woff2` | 9 | Inter (7 splits) + Outfit (2) self-hosted |
| `.br/.gz` | 4+4 | Precompressed `app.css`, `app.js`, `tools.js`, `tools.utils.js` |
| `.yaml` | 3 | `data/tools.yaml` (5464 lines), `data/blog.yaml` (11114 lines) |
| `.css` | 3 | `src/input.css` (1871 lines), `static/css/app.css`, `fonts.css` |

Key infra: `app/main.py:258`, `app/core/middleware.py:424`, `app/services/sitemap_service.py:270`, `Caddyfile`, `gunicorn_conf.py`, `storybrain-ai.service`, `deploy.sh`, `Makefile`, `.env.example`, `pyproject.toml`, `requirements.txt`, `package.json`.

## 2. Function / Route Inventory

**`app/main.py:47-258`** — `lifespan()` (warm `ToolDataLoader`, pre-import `rembg/cv2/prophet`, pool init, job reaper); 12 middlewares (outermost `TrustedHostMiddleware`, innermost `OriginCheckMiddleware`); `CachedStaticFiles` (hashed `.[8hex]` → immutable 1y, `sw.js` no-cache, `manifest/ads.txt` 86400, else 3600); routers in order: `health, seo, blog (before pages catch-all), pages, tools_image/pdf/crypto/fng/proxy/nft, analytics, jobs`.

| Router | Key functions |
|---|---|
| `api/routes/seo.py:18-55` | `GET\|HEAD /sitemap.xml, /robots.txt, /llms.txt` (3600s, `to_thread`) |
| `api/routes/pages.py:105-369` | `home(/)`, `tools_page`, `html_sitemap(/sitemap)`, `POST /api/contact`, `get_tool(/tool/{slug})` passes only `seo_data` (`pages.py:305-315`), `get_page(/{page_name})` + `pdf-tools→301` |
| `api/routes/blog.py:49-217` | `blog_index` (20/page), `blog_pillar`, `blog_post` (ETag+304, 3600s) |
| `api/routes/health.py:19-81` | `/healthz, /readyz, /versionz, /metrics` (internal-guarded) |
| `api/routes/analytics.py:32-59` | `POST /api/track`, `GET /api/analytics/top` |
| `tools_crypto/fng/image/pdf/proxy/nft/jobs` | predict/analyze crypto, `/fng`, remove-bg/watermark (sem 3), pdf convert (5 MB), proxy (10/min), NFT, job status |

**Middleware `app/core/middleware.py`** — `RequestID:57`, `OriginCheck:75`, `SecurityHeaders:124` (per-req nonce), `RateLimit:150` (60/min API, 200/min heavy GET), `MaxBodySize:299`, `CleanQuery:379` (301 strips `utm/fbclid/gclid/pagespeed`), `CaseSensitiveRedirect:408` (308 lower), `NoIndexAPI:419`.

## 3. Tool Audit — 107/107 PASS

- Categories: Calculators 26, Developer & SEO 26, Productivity & Utilities 20, AI & Crypto 16, Business & Operations 10, Image Processing 9.
- `app_category`: Finance 42, Developer 26, Utilities 20, Business 10, Multimedia 9.
- `sitemap_priority`: 0.8×46, 0.7×34, 0.9×25, 0.85×2.
- Templates: **107/107 present, 0 missing** (`templates/tools/<slug_underscored>.html`).
- `related_slugs`: **0 broken** (all resolve within 107).
- FAQs 2–10 (avg 5.4), howto 3–9 (avg 4.2), keywords 7–10 (avg 7.2), description 51–157ch (avg 104ch), 0 duplicate descriptions/names.
- `date_modified`: 104× `2026-10-02`, 3× `2026-09-25`. `about_body` + `howto_calculate` present for all 107.
- Most common FAQ stems: `how accurate are the results? (22)`, `predictions? (15)`, `data refreshed? (15)`, `data secure? (15)` — expected template reuse, not an error.
- 30 tools lack `2026` in keywords (e.g. `age-calculator, base64-tool, calculator, pdf-merger`) — harmless; year-stuffing not required.

### 3.1 Title-length check (simulated `seo_service.py:101-115` rules)

**29/107 rendered `meta_title` >60ch** (Google rewrites/truncates; not a penalty but fixable). Examples:

- `image-background-remover` 73ch, `image-to-text` 77ch, `expense-tracker` 64ch, `password-generator` 67ch, `paraphrasing-tool` 69ch, `color-palette-generator` 62ch, `json-formatter-validator` 65ch
- Cause: ` - Fast & Private Browser Utility | StoryBrain AI` (44ch suffix) and ` - Free SEO Tool Online | StoryBrain AI` (38ch) leave only ~16–22ch for tool names.
- Note: `test_meta_title_length` (`tests/test_keywords_no_cannibalization.py:90-96`) only checks raw `meta_title` overrides in YAML, NOT rendered titles from `seo_service.py` — hence green CI despite 29 rendered overflows. Recommend extending the test to rendered titles.
- **63/107 descriptions <120ch** (short but valid; 0 exceed 160ch, so no truncation risk).

## 4. Blog Audit — 87/87 PASS

- Pillars: developer-seo 30, business-operations 20, calculators 10, ai-crypto 9, image-processing 9, productivity-utilities 9 (+6 overviews: `calculators-pillar`, `ai-crypto-complete-guide`, etc.).
- Dates: 0 malformed. FAQs 6–10 (avg 7.6), howto 3–6 (avg 3.5), keywords 3–12 (avg 8.1).
- Links: **0 broken `tools[]` refs, 95 unique `/tool/` body links with 0 broken, 0 broken `related_posts`**.
- Titles 40–60ch (avg 55 — optimal). Descriptions 98–188ch (avg 145 — optimal).
- **All 87 share `/static/og-image.webp`** — correct fallback, but per-post images would improve CTR (P2).

## 5. SEO Audit

### Meta / OG (`templates/base.html:1-106`) — PASS
Title from `seo_data.meta_title`, description/keywords, canonical (`/tool/<slug>` else path), `og:locale en_US`, `og:type website`, OG WebP 1200×630 + JPG fallback, Twitter `summary_large_image`, `robots index,follow` overridable, `hreflang en + x-default`, theme-color, manifest, speculation-rules prefetch.

### Schema — PASS (single-source since 2026-10-05)
Live render (`TestClient`): all 107/107 tool pages → 200 with `SoftwareApplication` schema; visible FAQ count == YAML FAQ count on every page.
**MERGED 2026-10-05 (was: 44 `{% block seo_schema %}` overrides with divergent hardcoded FAQs shadowing `tools.yaml`, 41/44 zero question overlap):** template FAQs/howto merged into `data/tools.yaml` (template-first order, YAML-only extras appended, 10-FAQ cap enforced), `howto_calculate` + `about_*` unified to the previously-visible template copy (4 title-case fixes: API/MRR/SIP/YouTube), `app_sub_category: Writing Tool` preserved for 3 tools (new YAML field + `SeoService._from_raw` passthrough, `seo_service.py`), 4 valid related links absorbed (`uuid-generator`→api-tester, `percentage-calculator`→mrr/profit-margin, `calculator+age-calculator`→love, `emi-calculator`→mortgage). All 44 override blocks deleted; `base.html` renders `seo_data` for all 107. Side-effect fixes: mortgage page no longer links 2 nonexistent tools (`debt-snowball/debt-payoff-calculator` 404s); schema `datePublished` now uses fresher YAML dates (templates carried stale 2026-06/07 dates); About section restored on 29 pages whose overrides dropped it.
Trimmed to respect the 10-FAQ policy (11 FAQs dropped, tail of template lists — restore by raising cap if wanted): profit-margin 3 (`How much more volume...`, `Scenario Comparison`, `Price Sensitivity`), salary 3 (`freelance hourly rate`, `savings grow`, `free?`), scientific 1 (`free to use?`), youtube 4 (`other revenue streams`, `Revenue Breakdown tab`, `niche benchmarks`, `Compare tab`).
Earlier hygiene (same day): removed 2 truly-dead `{{ tool_seo_all(seo) }}` calls (`page_grader`, `social_media_post_preview`) + 6 unused imports.
`tool_base.html` (138 lines) is **orphan — 0 of 107 tool templates extend it; all 107 extend `base.html` directly**. Either wire it up or delete to avoid drift.

### Sitemap / robots / llms — PASS
`sitemap_service` invocation: **215 URLs, 215 unique, 0 dupes**, ~41.5 KB. `robots.txt` allows `/sitemap.xml`, disallows `/api/, /offline, /*?*, /pdf-tools` + `Sitemap:` line. `llms.txt` 215 lines. Single `sitemap.xml` is fine at this scale (<50k).

### Canonical / i18n / misc
`CleanQueryMiddleware` + apex `{path}` redirect consolidate `?utm/fbclid` dupes (correct). `keywords` meta still emitted (harmless bloat). Hardcoded `107+` fallbacks in `base.html:6,35` vs dynamic `index.html` count (stale-count risk on growth). `WebSite SearchAction ?q=` has no server handler (JS dialog uses `/api/tools/catalog`) — keep or point to `/tools`.

## 6. Technical Audit

### Performance
- `static/css/app.css` **362.8 KB** (br 34.5 / gz 43.2), `app.js` 52.1 KB, `tools.js` 40 KB, `tools.utils.js` 25.5 KB. Vendor **`apexcharts 586.7 KB + chart 203.6 KB` lazy-loaded on user action only** (`crypto_price_prediction`, `mrr_calculator`) — acceptable; never on critical path.
- Fonts self-hosted + preload ×2, no cross-origin preconnect needed. `content-visibility:auto` + IO reveal. GA/AdSense consent-gated lazy. Charts lazy. Images `loading=lazy` except blog cover `fetchpriority=high` (correct).
- **HTML `Cache-Control: private, no-cache, no-store, must-revalidate`** (verified live) — required for per-request CSP nonce rotation; trades edge-cacheability for security. Document as intentional.
- TODO (pre-existing): non-hashed `app.css/app.js?v=` (`package.json:6`, `scripts/build.js:4-5`, `Caddyfile:63-65`); SW static cache exact-match breaks `?v=` — migrate to content-hashed filenames when convenient.

### Accessibility — PASS
Skip-link, `main#main-content`, breadcrumb `aria-current`, search `combobox/listbox/live-polite`, cookie dialog `role=dialog` (no `aria-hidden`+focusables trap), `aria-modal`, all `img alt` present, `focus-visible`, 44px targets, `prefers-reduced-motion` (`input.css:241-261`). Gaps (P2): drawer focus-trap missing (`base.html:339-372`), gradient-text contrast to spot-check.

### Security / headers — PASS
Live: CSP `default-src 'self'...` + nonce, HSTS `31536000 includeSubDomains preload`, `X-Robots-Tag: noindex, nofollow` on `/api/tools/catalog` (verified). Fail-closed prod (`SECRET_KEY`/`ALLOWED_HOSTS` reject `*` — verified by validation error during audit). `TrustedHost` outermost, CORS `GET/POST/OPTIONS` no credentials, `OriginCheck` 403 cross-origin writes. Alignment TODOs: Caddy `Permissions-Policy` omits `interest-cohort=()` present in app header; Caddy lacks `COOP/CORP/CSP` (app-only) — ensure Caddy always in front in prod; no CSP `report-uri` (`middleware.py:47` TODO).

### Deps / tests / lint
- Pinned: `fastapi 0.136.3`, `uvicorn 0.49`, `jinja2 3.1.6`, `tailwind 4.3.1`, `daisyui 5.5.23`, `esbuild 0.28`. Heavy ML (`rembg/cv2/prophet`) optional via `deploy.sh`, lifespan pre-import — watch worker RSS.
- **201 tests collected**; sampled `csp/tools/sitemap/blog` suites PASS (full run exceeds 120 s on Win — run `make test` in CI).
- **`ruff check app` → 78 errors** (mostly `SIM105` `try-except-pass` → `suppress`, e.g. `proxy_service.py:269`); 40 auto-fixable.

## 7. Deep-Audit Findings (ranked)

**P1 — cleanup (no user impact today, fix to prevent drift):**
1. ~~44× `{% block seo_schema %}` overrides~~ DONE 2026-10-05 (see §5). Remaining P1: `tool_base.html` orphan (below).
2. ~~`templates/tool_base.html` orphan~~ DELETED 2026-10-05 (0 templates extended it; all 107 extend `base.html`; removed from `test_csp_no_inline_handlers.py:BASE_TEMPLATES`).
3. ~~15× `onclick=` files~~ RESOLVED 2026-10-05: all were benign JS property assignments (`el.onclick = fn`, CSP-allowed) or comments — zero real `onclick` attributes existed. Found and fixed REAL handlers instead: `qr_generator` 3× `onchange/oninput` → delegated `data-action` (logo upload, 2 sliders; stale TODO removed); 6 files' `onmouseover/onmouseout` hover styling → CSS `:hover` + `!important` (image_compressor/converter, love, mortgage, mrr, watermark_remover); 10× `onerror` in JS-generated preview HTML → `data-img-fallback-html` + document capture-phase error listener (open_graph, serp, social_media_post_preview); 2× dead `onerror="this.innerHTML=..."` on void `<img>` removed (no-op). `GLOBAL_BANNED_RE` extended to full handler list (12 events) so CI guards all of it.
4. 15× hardcoded `{% block og_image %}` overrides pointing at shared `og-image.jpg` — harmless duplication; centralize or give per-tool images.

**P2 — SEO CTR / polish: DONE 2026-10-05 with one important correction.**
ARCHITECTURE FINDING (verified by live render): per-tool template blocks `title`, `meta_description`, `meta_keywords`, `canonical_url`, `og_title`, `og_description`, `twitter_title`, `twitter_description` are DEAD — `base.html:6,16-17,29,35-36,53-54` wraps them in `{% else %}` branches that never evaluate because `get_tool` always passes truthy `seo_data` (`pages.py:314`). Rendered title/desc/OG come 100% from `tools.yaml` via `SeoService`. (This invalidates any template-block length audit — the 38 "long template titles" never reach crawlers.) Recommend deleting the dead blocks in a future pass (they mislead editors); left untouched to limit churn.
What was fixed in the LIVE path: 29 `meta_title` YAML overrides added (all rendered titles now ≤60ch; `test_meta_title_length` green), 64 short YAML descriptions expanded to 120–160ch (all rendered meta descriptions now in range; uniqueness + boilerplate gates green), 15 `og_image` + 15 `twitter_image` overrides deleted (they forced jpg-only and dropped the webp primary + `secure_url`; webp+jpg chain restored, verified live).
7. Single shared OG image for 107 tools + 87 posts — needs real design work (per-category images); not producible in this environment.
8. `SearchAction ?q=` target 404s — point to `/tools` or drop the annotation.

**P3 — perf/tech debt:**
9. Hashed filenames, `media=print` CSS split, `decoding=async`, SW `ignoreSearch` for `?v=`.
10. `ruff` 78 errors; 7 root `fix_*.py` one-off scripts (candidate `scripts/archive/` or delete); `thesaurus.json` 237 KB unused by critical path (confirm lazy).

## 8. Action Plan (proposed order)

- [x] P1.1a (done 2026-10-05): removed 2 truly-dead `tool_seo_all(seo)` calls + 6 unused imports (zero content change).
- [x] P1.1b (done 2026-10-05): merged 44 template FAQ/howto sets into `data/tools.yaml`, deleted override blocks, added `app_sub_category` support. Verified: 27/27 content/schema/csp tests pass; 107/107 pages render with schema; FAQ counts match YAML.
- [ ] P1.2: decide `tool_base.html` fate (adopt vs delete).
- [x] P1.2 (done 2026-10-05): deleted orphan `tool_base.html`; updated CSP test list.
- [x] P1.3 (done 2026-10-05): qr delegated handlers, hover→CSS, onerror→capture listener; test regex extended to 12 events.
- [x] P2 titles/descs/images (done 2026-10-05): 29 YAML `meta_title` overrides, 64 YAML descriptions to 120–160ch, 30 redundant image blocks deleted. 39/39 tests green.
- [ ] P2 (future): per-category OG images (design task); delete dead template head blocks (title/meta/og_title/og_description ×107) to stop misleading editors.

## 9. Product Expansion — 10 New Tools (2026-10-05, multi-agent)

Process: Agent A (long-tail gap research over 1472 normalized keywords) → Agents B+C (YAML content packs) → validation scripts → implementation → Agent D (independent cannibalization + AEO/GEO audit) → fixes → 66/66 tests green.

New tools (107 → 117): delivery-challan-generator, meeting-cost-calculator, freelance-rate-calculator (Business, 10→13); image-exif-remover, image-blur-pixelate-tool, photo-collage-maker (Image, 9→12); bmi-calculator, fuel-cost-calculator (Calculators, 26→28); hash-generator (Dev&SEO, 26→27); pomodoro-timer (Productivity, 20→21).

- Long-tail: 80 keywords, zero exact collisions vs catalog+blog (normalized check); caps respected (≤8/tool).
- LSI woven into about/FAQ copy (entity-distinct; auditor confirmed stems isolated: challan/collage/pomodoro/freelance/meeting/exif/blur/hash/fuel/bmi).
- AEO: 60 FAQs, all interrogative-start, answer-first, 25-60 words; 2 audit FIXes applied (fuel Q6 rephrased; pomodoro ADHD claim softened + disclaimer).
- GEO: entity+audience+privacy about blocks; real formulas in all `howto_calculate`.
- Templates: 10 working client-side tools (MD5 unit-tested vs hashlib vectors incl. unicode; canvas brush/pixelate/collage/EXIF-strip logic reviewed); zero inline handlers; node syntax-checked; all render 200 with schema.
- Links: every new tool indegree ≥2 (incl. old-tool backlinks e.g. eway-bill→challan, salary→meeting/freelance); zero orphans catalog-wide.
- [ ] P1.3: migrate 15 `onclick=` files to `data-action` (per-file, test each tool manually).
- [ ] P2: title/desc pass on 29 + 63 tools via `data/tools.yaml` (+ `test_content_quality.py`, `test_keywords_no_cannibalization.py` must stay green).
- [ ] P2: per-category OG images + wire `seo_service.image_url`.
- [ ] P3: hashed assets + SW `ignoreSearch`, `ruff --fix`, archive `fix_*.py`.

## Appendix — How This Was Verified

- `audit_tools.py`: TOOLS=107, categories/app_category/priority counters, 0 missing templates, 0 broken related, faq/howto/keyword stats.
- `audit_blog.py`: POSTS=87, pillar split, 0 bad dates, 0 broken tool/related/body links, 95 unique body `/tool/` links.
- `audit_seo.py`: 29 titles>60, 63 desc<120, 0 desc>160, 0 dup desc/name.
- `audit_tpl.py`: 107 extend `base.html`, 46 legacy `seo` var, 15 `onclick`, 15 `og_image` overrides.
- `audit_sitemap.py`: 215 URLs / 215 unique / 41.5 KB.
- `audit_render.py`: 200s on `/`, 2 tools, `/blog`, `/sitemap.xml`, `/robots.txt`; 4 ld+json blocks; CSP/HSTS/noindex verified.
- `pytest --collect-only`: 201 tests; `ruff check app`: 78 errors.

Scripts retained in `C:\Users\AFOX\AppData\Local\Temp\opencode\audit_*.py` (not committed).
