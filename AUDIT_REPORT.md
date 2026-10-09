# StoryBrain AI — Full Deep Audit Report

> Generated: 2026-10-05 (Build mode, verified by execution). Updated: catalog 107 → 117 tools; blog 87 → 99 posts.
> Addendum 2026-10-08 (Build mode, verified by execution): boilerplate-elimination + intent-split pass over `data/tools.yaml` / `data/blog.yaml` — see §11. All suites below re-verified green.
> Scope: full code / files / folders / functions / tools / blog / SEO / technical / security / deep audit + product expansion
> Method: `data/tools.yaml` + `data/blog.yaml` parsed with PyYAML, template grep, `TestClient` render checks, sitemap service invocation, `pytest --collect-only`, `ruff check`.

## Executive Summary

| Area | Verdict |
|---|---|
| Content integrity (tools/blog links) | **PASS** — 0 broken `related_slugs`, 0 broken blog→tool refs, 0 broken `/tool/` body links, 0 broken `related_posts`, 117/117 templates present, min indegree 2 (0 orphans) |
| Sitemap / robots | **PASS** — 237 unique URLs (117 tools + 99 posts + hubs/pages), 0 duplicates, valid XML, correct disallows; YAML source-of-truth, full `/blog/pillar/slug` changefreq, dynamic `llms.txt` count |
| SEO blocking issues | **NONE** — no noindex on HTML, correct canonical, CSP nonce present, 4× `ld+json` blocks per tool page as designed; all tool descs 120–160ch, all blog descs 120–160ch, 0 rendered titles >60ch |
| Cleanup debt (non-blocking) | **DONE 2026-10-05 + 2026-10-08: 44 `seo_schema` overrides merged; `tool_base.html` deleted; inline handlers eliminated; 29 `meta_title` + 64 descriptions fixed; 30 image blocks deleted; 2026-10-08: generic FAQ/howto boilerplate removed (see §11), 13 blog descs fixed, orphan backlinks added, cache tiers aligned, counts 107→117 everywhere. Remaining: per-category OG images (needs design work)** |
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

## 10. Blog Expansion — 12 New Posts (2026-10-05, multi-agent)

Process: Agent A (long-tail research over 1552 normalized keywords) → Agents B+C (drafting 6+6, one truncated agent output + one missing post recovered via targeted re-draft) → scripted gate validation mirroring every blog test → insertion → Agent D (independent audit) → 102/102 tests green + 12/12 SHIP.

New posts (87 → 99; thin pillars 9-10 → 12-13 each): bmi-by-age-chart-explainer, fuel-cost-per-km-india-planner, emi-vs-sip-vs-fd-decision (calculators); md5-vs-sha-hashing-beginner, fear-greed-sentiment-reading, meme-coin-red-flags-learn (ai-crypto); exif-gps-strip-privacy, face-plate-blur-privacy, collage-grids-layout (image-processing); pomodoro-exam-season-focus, habit-streak-system, meeting-cost-audit (productivity-utilities).

- Long-tail: 108 keywords, zero exact collisions vs 117 tools + 87 old posts; 3 near-dup pairs reviewed ACCEPT (hub-spoke intent split, e.g. emi-vs-sip-vs-fd framework vs sip-vs-fd planner).
- AEO: 76/76 interrogative FAQs, answer-first, 25-60 words, ≤2 tool links/answer; zero unverified stats/promises.
- GEO/YMYL: entity+audience framing; strict disclaimer sentences on all 6 finance/health/crypto posts; zero personalized recommendations; no `financial advice` Q.
- Structural: 12/12 exactly-one-table (caption+thead+3th), no chrome H2s/ids, first-H2 dissimilar, all tools[]/related_posts[] resolve, pillar OG images, ETag + BlogPosting/FAQPage schema verified live.
- Cross-link: 12/12 posts anchor ≥1 new tool; sitemap auto-includes (105 blog URLs); pagination/index/pillars unaffected (pillar pages unpaginated).
- [ ] P1.3: migrate 15 `onclick=` files to `data-action` (per-file, test each tool manually).
- [ ] P2: title/desc pass on 29 + 63 tools via `data/tools.yaml` (+ `test_content_quality.py`, `test_keywords_no_cannibalization.py` must stay green).
- [ ] P2: per-category OG images + wire `seo_service.image_url`.
- [ ] P3: hashed assets + SW `ignoreSearch`, `ruff --fix`, archive `fix_*.py`.

## 11. Addendum 2026-10-08 — Boilerplate Elimination + Intent-Split Pass

Scope: `data/tools.yaml` (117), `data/blog.yaml` (99), `app/services/sitemap_service.py`, `Caddyfile`, template/doc counts. All changes verified by `yaml.safe_load`, keyword/content/sitemap/blog/api/middleware/csp suites green (16 + 19 + 62 + 31 passed in-session).

### 11.1 Keyword intent splits (Jaccard ≥0.6 → <0.45, exact collisions stay 0)
- calculator: 3 intent-colliding keywords replaced with calculator-specific long-tails (keyboard/memory/offline); compound `howto_calculate` + about now carry FV formula, Rule of 72, SIP-vs-lumpsum LSI; credit-utilization FAQs/about now CIBIL/paydown math; crypto-password-generator decontaminated (market FAQs/howto → entropy/seed/offline/BIP39).
- Tool↔blog pairs split tool=do / blog=learn: airdrop finder/checker (0.75→0.12), EMI 15v20 amortization (0.67→0.42), safe-EMI framework (0.70), mining break-even months (0.75→0.21), meme order-book reading (0.75→0.23), FD-TDS estimator (0.78→0.23).

### 11.2 FAQ/howto boilerplate removal (`tools.yaml` net −300+ lines)
- Generic "How does X work?" 11→0 and "transparent calculation logic" accurate-answers 14→0 across finance cluster (burn, CAC, date, debt, e-way, FD, GST, instagram, loan, MRR, percentage, adsense, age, EMI) — all now formula-specific with title-case acronyms fixed.
- Generic howto triples removed where specific steps existed: finance triple (11 tools), crypto `Select Asset/Configure Settings/Review Analysis` (13 tools, 14×→0), dev `Enter Input/Generate/Copy-or-Download` (6 tools, 10×→0), doc `Fill Details/Customize/Download PDF` (8 tools incl. invoice), setup triple (4 tools).
- Solo-generic triples renamed to tool-specific: uuid, schema, robots-txt, sitemap, note, pdf-converter, random, resume-analyzer, task-manager, calculator (keyboard/memory), e-way/FD/loan, price-prediction bands, meme/image steps, doc "Brand and Print" per-type.
- Max howto-title repetition 23×→5× (remaining 5× are legitimate workflow verbs with distinct descs). Generic howto descs 22→0. `test_no_duplicate_howto_titles_within_tool` green throughout.

### 11.3 Thin-content expansion
- About <50 words: 17→0 (all 117 now 50w+ with LSI: RSI/MACD, FIFO/TDS, honeypot audits, JSON-LD types, XMP, fee-aware totals).
- FAQ answers <15 words: 60→0 (crypto refresh split live-vs-local, offline ×15 per-tool, doc download/valid/customize per-type, pdf-metadata dup Qs merged 9→7, QR/sip/color/seo/text-server expanded).
- Blog descriptions out-of-range 13→0 (all 99 now 120–160ch). Orphan indegree: 8×1 → min 2, 0 orphans.

### 11.4 Technical fixes
- `sitemap_service.py`: YAML source-of-truth discovery, explicit changefreq (bare/`/tool/`→weekly, `/blog/`→monthly), full `/blog/pillar/slug` key, dynamic `llms.txt` tool count → 237 URLs live-verified.
- `Caddyfile`: `app.js/app.css` 31536000→3600 `must-revalidate` to match `app/main.py:185`.
- Counts 107→117: `base.html`, navbar, footer fallback, search placeholder, about stat, 404 meta, `manifest.json`, `README.md`, `AI_CONTEXT.md`, `package.json`, `pyproject.toml`.
### 11.5 Bing Webmaster round (2026-10-09) — short meta descriptions + IndexNow
- Bing flagged "Meta descriptions on many pages are too short" (rule 118) on ~17+ `/tool/` URLs. Root cause: production HTML (verified live for `/tool/job-card-generator`, 128ch) predates the length pass — all flagged pages sat at 121–148ch. Fix: all 117 tool descriptions lengthened to 150–160ch (0 dupes), render-verified via `TestClient` (job-card 128→150, calculator →150, mining →159, invoice →160). Takes effect on next deploy + Bing recrawl.
- IndexNow was unimplemented (repo grep: 0 hits) — explains "recently published pages were not submitted via IndexNow". Implemented: `Settings.INDEXNOW_KEY` (`app/core/config.py`), `GET /{key}.txt` key file in `app/api/routes/seo.py` (exact routes take precedence; non-hex/wrong-key → 404), stdlib `scripts/submit_indexnow.py` (`--url/--url-file/--sitemap-url/--all/--dry-run`, 10k chunks), `.env.example` + README docs, 5 tests in `tests/test_indexnow.py` green. Still required from the user: generate key, set in `.env`, deploy, optionally register in Bing portal, then `--all` submit.
- "Not enough inbound links from high quality domains" is off-site (no code fix): recommended — submit sitemap in Bing/GSC post-deploy, IndexNow `--all`, blog cross-posts, and directory listings; track clicks/impressions baseline (6 / 499 at time of report).
### 11.6 GSC query round (2026-10-09) — 17 clicks / 4.48K impressions / 0.4% CTR / pos 45.3
- Biggest pool: crypto-tax variants (~1,500 impressions, pos 70–90, 0 clicks). `crypto-tax-calculator` keywords reworked to GSC-proven heads (`crypto tax calculator`, `free crypto tax calculator`, `crypto capital gains tax calculator`, `bitcoin tax calculator`, `crypto tax estimator` + retained India/FIFO terms, 7→8) + estimator FAQ (9→10, at cap). All new keywords collision-checked CLEAN vs tools/blog.
- Page-1 winners reinforced: `seo-writing-assistant` +`seo writing assistant free` keyword (36 imp, pos 34) + free FAQ (targets the pos-4.59 "is seo writing assistant free" query); `meme-generator` +`meme maker online free`; `mortgage-overpayment-calculator` +`mortgage calculator extra payment`; `eway-bill-calculator` +`e-way bill validity distance calculator`; `quotation-generator` swapped to `proforma invoice vs quotation` (pos 3.87). Receipt (pos 4.37) already exact-matches, left untouched.
- Watch: `css-gradient-text-generator` earned clicks at pos 91 (new page, leave to climb); Hindi `ईवे बिल` query noted as future i18n/blog opportunity; 24h view (103 imp, pos 18.3) shows the impression surge is current.
### 11.7 AdSense low-value-content round (2026-10-09) — thin + copy-paste sweep
- Thinnest pages by rendered words raised (floor 167→211, avg 384→391): `json-formatter-validator` 2→6 FAQs; note/pdf-converter/resume-analyzer/task-manager/habit/sitemap/robots/expense/uuid/password/meme 4→6 tool-specific FAQs (the five storage-template and three output-template FAQ clones now lead with specific content).
- Template-clone abouts rewritten: 7 doc generators (purchase/sales/service/work-order/job-card/receipt/invoice, Jaccard up to 0.96→~0.15), image-converter/pdf-converter, mining/profit, note/product/resume-analyzer, uuid/airdrop/nft/robots/schema. About<50w: 17→0 (all dense and unique; residual ~0.6 Jaccard pairs share vocabulary, not prose).
- Factually-wrong crypto FAQs fixed across all 14 crypto tools: market-data/prediction boilerplate replaced with per-tool local-vs-live accurate answers (secure answers got unique tails). Shared-answer max now 20x short trust boilerplate (within the >30 gate; pages carry 350+ unique words otherwise).
- Ads: `ads.txt` valid (single DIRECT line, served with cache headers); AdSense loads consent-gated + lazy (no layout shift, no hardcoded slots — Auto Ads governed from dashboard, keep ad load moderate). No doorway issues: similar tools are functionally distinct with differentiated copy.
### 11.8 Blog depth round (2026-10-09) — thinnest-post expansion
- 8 thinnest favicon-cluster posts expanded with 3 appended practice paragraphs each (no new H2/tables/ids, all internal-link and sanitize safe): dark-mode 380→602, emoji 445→617, favicon-vs-og 443→621, generator-vs-manual 479→649, size-guide 493→655, apple-touch 605→772, svg-support 670→840, pwa-manifest 737→950+. All 27 `test_blog.py` green + live render 200 with ETag verified.
- Root `fix_*.py` archived to `scripts/archive/` (gitignored). No dead `{% block %}` overrides remain in `templates/tools/` (verified by grep — base else-branches are intentional non-tool fallbacks).

## Appendix — How This Was Verified

- `audit_tools.py`: TOOLS=107, categories/app_category/priority counters, 0 missing templates, 0 broken related, faq/howto/keyword stats.
- `audit_blog.py`: POSTS=87, pillar split, 0 bad dates, 0 broken tool/related/body links, 95 unique body `/tool/` links.
- `audit_seo.py`: 29 titles>60, 63 desc<120, 0 desc>160, 0 dup desc/name.
- `audit_tpl.py`: 107 extend `base.html`, 46 legacy `seo` var, 15 `onclick`, 15 `og_image` overrides.
- `audit_sitemap.py`: 215 URLs / 215 unique / 41.5 KB.
- `audit_render.py`: 200s on `/`, 2 tools, `/blog`, `/sitemap.xml`, `/robots.txt`; 4 ld+json blocks; CSP/HSTS/noindex verified.
- `pytest --collect-only`: 201 tests; `ruff check app`: 78 errors.

Scripts retained in `C:\Users\AFOX\AppData\Local\Temp\opencode\audit_*.py` (not committed).
