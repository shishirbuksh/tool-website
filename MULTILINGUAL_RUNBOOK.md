# Multilingual Release Runbook

This document is the operational contract for releasing HI / ES / FR / DE.
The code defaults to **quarantine**: every non-English URL is crawlable
(`200`) but served `noindex, follow`, with no hreflang, no sitemap entry and no
IndexNow submission.

## Source of truth

| Concern | File |
| --- | --- |
| Locale release + surface/static allowlist | `data/locale_publication.yaml` |
| Per-item translation status / review provenance | `data/tools.yaml`, `data/blog.yaml` |
| Indexability policy | `app/core/locale_policy.py` |
| Pre-release quality checks | `scripts/quality_gate.py` |
| Readiness / blocker backlog | `scripts/locale_backlog.py` |
| DE + ES batch 1 plan and worksheet | `MULTILINGUAL_BATCH_1.md`, `data/keyword_research_de_es_batch1.csv` |
| Rendering / headers | `app/api/routes/pages.py`, `app/api/routes/blog.py`, `templates/base.html` |
| Sitemaps, robots, hreflang | `app/services/sitemap_service.py`, `app/api/routes/seo.py` |

A localized URL is indexable only when **both** gates pass:

1. The locale is `status: published` in `data/locale_publication.yaml`.
2. The item's `i18n.<locale>` block has `translation_status: published` and is
   not marked `noindex: true`.

Missing/legacy overrides are treated as quarantined. This is deliberate: the
previous presence-based check indexed thin machine translations.

## Localized content pack fields

Every override that will be released must carry:

```yaml
i18n:
  de:
    name: "Kreditrechner"
    meta_title: "..."
    description: "..."
    keywords: ["Kreditrechner", "Tilgung", "Zinsen", "Laufzeit"]
    body_html: "<h2>...</h2>..."       # blog
    about_body: "..."                 # tools
    faqs: [...]
    translation_status: published     # draft | review | published
    reviewer: "Native reviewer name"
    reviewed_at: "2026-10-28"         # YYYY-MM-DD
    author: "StoryBrain AI"
    sources: ["https://..."]          # required for YMYL packs
```

Do not set `translation_status: published` before the native reviewer signs off.
Do not release a locale while its surfaces still render English chrome.

## Content pack workflow

Content packs live in `data/content_packs/`. The applier replaces only the
target `i18n.<locale>` block, preserves CRLF and unrelated bytes, and verifies
the semantic before/after state. Dry run is the default.

```bash
# Validate and preview
python scripts/apply_content_pack.py data/content_packs/de_wave1a.yaml

# Apply
python scripts/apply_content_pack.py data/content_packs/de_wave1a.yaml --write

# Audit exactly the pack's slugs
python scripts/quality_gate.py --pack data/content_packs/de_wave1a.yaml
python scripts/quality_gate.py --pack data/content_packs/es_wave1a.yaml
```

Rules:

- A pack must declare its `locale`, `wave`, tools/posts and complete override
  fields. The applier errors on a missing slug, missing section or malformed
  reviewer/date pair.
- The applier refuses to overwrite `translation_status: published` unless
  `--allow-published` is passed.
- It errors if any unrelated item or locale would change.
- Keep `translation_status: review` and leave `reviewer`/`reviewed_at` empty
  until native sign-off.
- `--pack` infers the locale and audits only the pack's slugs. Do not use
  `--status review` for a batch audit: legacy overrides with no
  `translation_status` default to `review`, so that filter selects all 216
  items per locale.

## UI readiness gate

The content gate checks YAML, not rendered chrome. A locale is not releasable
while its calculator UI is English or US/India-centric. Before release, render
every wave-1a tool in DE and ES and verify:

- No hardcoded English visible text, placeholder, `aria-label`, toast, history
  or export string remains.
- Country-appropriate defaults and currency: EUR formatting through the
  locale-aware `Intl` path; no `$` output.
- The model is native, not just relabeled. DE/ES `loan-affordability-calculator`
  must render `loan_affordability_calculator_native.html` (net income,
  Kaufnebenkosten/purchase costs, Zinsbindung, 35/40/45 scenarios), never the
  US PMI/HOA/property-tax/DTI model.
- `src/js/tools.utils.js` must not override `base.html`'s locale-aware
  `formatCurrency` with the legacy USD/en-US implementation. The bundle must be
  rebuilt with `npm run build:js && npm run build:compress` after formatter
  changes.
- Shared chrome must be localized too: navbar/footer labels, breadcrumb,
  mobile bottom-nav and cookie-banner ARIA labels, plus the methodology and
  helpful-feedback block. These render on every tool page, so an English
  fallback here leaks across the whole batch.
- `/de/tools` and `/es/tools` still render English directory chrome. The first
  release keeps `surfaces: []` so they stay `noindex, follow`; localize them
  before adding the `tools` surface.

`python -m pytest tests/test_localized_calculator_ui.py -q` is the automated
gate for English chrome, `$` output, US affordability terms, locale defaults,
and English footer/methodology/ARIA labels.
The detailed per-template checklist is in
[`MULTILINGUAL_BATCH_1.md`](MULTILINGUAL_BATCH_1.md). This gate still needs a
native reviewer on mobile and desktop; it cannot be satisfied by metadata edits.

## Audit a batch

```bash
# One tool / post
python scripts/quality_gate.py --locale de --slug emi-calculator

# A rebuilt batch (exactly the pack's items)
python scripts/quality_gate.py --pack data/content_packs/de_wave1a.yaml

# A released batch (default statuses: review + published)
python scripts/quality_gate.py --locale de --status review --status published

# Full quarantine readiness report (expected to fail until rebuilt)
python scripts/quality_gate.py --all-locales

# Machine-readable report for the review ticket
python scripts/quality_gate.py --locale de --json > gate-de.json

# Readiness backlog for every localized override (CSV + JSON)
python scripts/locale_backlog.py --csv var/locale-backlog.csv --json var/locale-backlog.json

# Make targets
make locale-gate ARGS="--locale de --slug emi-calculator"
make locale-backlog ARGS="--locale de --locale es"
```

CI runs `python scripts/quality_gate.py --quiet` after the test suite and
uploads the locale backlog as an artifact. The gate only covers released
locales, so DE/ES/FR/HI join the blocking check automatically when their
`status` changes to `published`.

The gate enforces localized thresholds (not English baseline):

- Tool `about_body` >= 150 words; 5+ FAQs; answers >= 12 words.
- Blog body >= 800 words; 4+ H2; 4+ internal links; 5+ FAQs.
- No `LSI:` scaffolding, U+FFFD replacement characters, TODO markers or
  template placeholders.
- No body identical to English or reused across locales.
- Native-language signal (German/Spanish/French stopwords, Devanagari ratio).
- Unique meta titles/descriptions; declared keywords present in the copy.
- Reviewer, review date, author and sources present.
- Released sitemaps only contain indexable URLs; hreflang clusters match the
  policy; released surface pages are present; quarantined locales are absent
  from sitemap index/robots.

Warnings do not fail the gate unless `--strict` is passed. Errors always fail.

## Release procedure

1. Native reviewer signs off the pack; fill `reviewer`, `reviewed_at`,
   `author`, `sources`, and set `translation_status: published`.
2. Run the pack gate and the UI readiness gate. The gate must print `PASS`
   (use `--strict` for a zero-warning release), and the rendered DE/ES
   calculators must contain no English or US/India-centric chrome.
3. Set the locale to `published` in `data/locale_publication.yaml` and add only
   the surfaces you are ready to index:

   ```yaml
   locales:
     de:
       status: published
       surfaces: []
   ```

   Start with `surfaces: []`: the 8 wave-1a **tool** pages index from their own
   `translation_status`, so the first deploy needs no hub chrome. Keep the
   wave-1a **blog** item at `translation_status: review`; its post template
   still renders English chrome (Published/Updated, min read, share, Key
   Takeaways, TOC, Related Guides, Methodology) and links India-only SIP/FD
   tools. Publishing it would expose English chrome on an indexed URL. Add
   `tools`, `blog` and `blog_pillars` only after `/de/tools`, `/de/blog`, the
   pillar hubs and the post chrome are localized. Add `home`/`hubs` only after
   their localized chrome is reviewed. Tool item pages do not depend on the
   surface list; the blog item must wait for post chrome.

   Leave `static` out until legal/static pages are actually localized (the
   Impressum / Aviso legal / Mentions légales are not translated yet). When a
   localized legal page is ready, release it individually:

   ```yaml
   locales:
     de:
       status: published
       surfaces: [home, tools, blog, blog_pillars, hubs, static]
       static_pages: [/impressum, /datenschutz]
   ```

   `static_pages` is a per-path allowlist: the `static` surface alone never
   advertises a static URL. The code-level safety net still blocks
   `/about`, `/contact`, `/privacy`, `/terms` and `/disclaimer` because those
   routes currently render the English body behind every locale. Remove a path
   from `static_pages` to quarantine that page without rolling back the locale.
4. Deploy, then verify:

   ```bash
   curl -sI https://www.storybrainai.com/de/tool/emi-calculator | grep -i robots
   # expected: no X-Robots-Tag once released

   curl -s https://www.storybrainai.com/de/tool/emi-calculator | grep hreflang
   # expected: de + en + x-default, no hi/es/fr

   curl -sI https://www.storybrainai.com/sitemap-de.xml
   # expected: 200

   curl -s https://www.storybrainai.com/sitemap-index.xml | grep sitemap-de
   curl -s https://www.storybrainai.com/robots.txt | grep sitemap-de
   ```

5. Submit the locale sitemap in Google Search Console and Bing Webmaster Tools.
   IndexNow only submits released locales (explicit URLs under a quarantined
   locale are skipped too):

   ```bash
   python scripts/submit_indexnow.py --key <KEY> --all --all-locales --dry-run
   python scripts/submit_indexnow.py --key <KEY> --all --all-locales
   ```

6. Monitor for 28 days: indexed URL count, impressions/queries, CTR, and
   manual actions. Check that Google selected the correct canonical and that
   the localized URL ranks instead of the English one for native queries.

## Rollback

Set the locale back to `status: quarantined` (or remove the surface from
`surfaces`) and redeploy. The app immediately serves `noindex, follow`, drops
the locale from sitemap index/robots/hreflang, and returns 404 for its sitemap.
Re-submit the sitemap index after rollback so search engines drop the URLs.

## Rollout order

1. **DE + ES** (loan/credit calculators first).
2. **FR**.
3. **HI** (Hinglish allowed; EMI keywords already match native demand).

Do not localize India-only tools (GST, E-Way Bill, SIP, FD, job card, delivery
challan) into DE/ES/FR. Keep English slugs in phase 1; revisit top slugs only
after six months of data.
