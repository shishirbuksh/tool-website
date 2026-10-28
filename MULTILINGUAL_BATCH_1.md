# DE + ES Batch 1 Plan

Status: **wave 1a rebuilt and applied; release blocked**. The ten DE/ES
wave-1a overrides pass the content gate with zero errors, but DE and ES remain
quarantined. Release is blocked on native reviewer sign-off, calculator UI
localization, and the remaining data/legal inputs (GSC/Bing/paid exports,
Impressum/Aviso legal entity details). The other 854 localized overrides are
still legacy machine drafts and remain blocked.

Companion worksheet: [`data/keyword_research_de_es_batch1.csv`](data/keyword_research_de_es_batch1.csv)

## Why this batch

DE and ES are the first release pair because they have the clearest native
demand for the finance calculators and do not depend on India-only tools:

- DE: `Kreditrechner`, `Ratenrechner`, `Sondertilgung`, `Zinseszins`,
  `Tagesgeld`, `Rentenlücke`.
- ES (Spain): `calculadora de préstamos`, `cuota`, `amortización`,
  `capacidad de endeudamiento`, `interés compuesto`, `cuenta remunerada`,
  `jubilación`.

This is a native rebuild, not a translation pass. The existing overrides are
thin machine drafts: tool bodies are ~20 words, blog bodies are ~200–280 words
with no H2 sections, and many carry `LSI:` scaffolding and four short FAQs.
They must be replaced, not repaired.

## Applied state (2026-10-28)

Wave 1a is written and applied, but not released:

| Item | DE | ES |
| --- | --- | --- |
| Tool body words | 289–345 | 306–368 |
| Tool FAQs | 6 each | 6 each |
| Blog body words | 1,177 | 1,128 |
| Blog H2 sections | 9 | 8 |
| Blog internal links | 8 | 8 |
| Blog FAQs | 7 | 7 |
| Declared keywords present | 6/6 on all five items | 6/6 on all five items |

- Packs: `data/content_packs/de_wave1a.yaml`, `data/content_packs/es_wave1a.yaml`.
- Applied with `python scripts/apply_content_pack.py <pack> --write`; a semantic
  diff against `HEAD` confirms only the ten intended overrides changed.
- `translation_status: review`; `reviewer` and `reviewed_at` are intentionally
  empty until native sign-off.
- Batch gate: `python scripts/quality_gate.py --pack <pack>` audits exactly five
  items and reports 0 errors. The only warnings are `missing_reviewer` and
  `missing_reviewed_at` on each item.
- Worksheet rows are `review_status: rebuilt_pending_native_review` and
  `release_status: quarantined`.
- The other 854 localized overrides are untouched and still blocked.

Where the cross-item keyword uniqueness test forced a variant, the pack uses
`cuota máxima` (ES loan affordability), `amortización parcial` (ES
overpayment), `Notgroschen` (DE debt) and `Restschuld` (DE overpayment) instead
of the worksheet seed. The worksheet keeps the original research terms; the
pack is the declared keyword set.

Do not use `--status review` alone to audit this batch: legacy overrides with no
`translation_status` default to `review`, so that filter selects all 216 items
per locale. Use `--pack` or explicit `--slug` values.

## Calculator UI readiness (implemented, pending native review)

Content alone does not make the locale releasable. The four wave-1a tool pages
were rebuilt so DE/ES render native chrome, EUR defaults and locale-aware
formatting. These are rendered-UI changes, not YAML metadata changes, so the
content gate cannot verify them; `tests/test_localized_calculator_ui.py`
protects them with rendered-HTML assertions.

| Template | Current state |
| --- | --- |
| `templates/tools/emi_calculator.html` | Fully localized: hero badge, inputs, summary, What-If, history, comparison, amortization, table headings, toasts, copy/export and `aria-label`s. DE/ES/FR defaults are EUR-based (DE 20,000 / 5.9% / 5y; ES 15,000 / 7.5% / 5y). Dates and numbers use the locale's `Intl` format. |
| `templates/tools/loan_affordability_calculator.html` | EN/HI (and FR until rebuilt) keep the US model. DE/ES are routed to `templates/tools/loan_affordability_calculator_native.html`: net income, existing debt payments, equity, Kaufnebenkosten/purchase costs, housing costs, fixed-rate period, comparison rate, 35/40/45 affordability scenarios, remaining balance after the fixed period and a localized annual amortization table. No PMI/HOA/property-tax/DTI terms render. |
| `templates/tools/mortgage_overpayment_calculator.html` | Fully localized chrome and table headings, EUR defaults for DE/ES/FR, localized currency names, payoff dates and scenario buttons, locale-aware currency formatting. |
| `templates/tools/debt_calculator.html` | Fully localized chrome, locale-specific default debts (DE: Ratenkredit/Kreditkarte/Autokredit; ES: préstamo personal/tarjeta/coche), EUR formatting, localized method names and best-method output. |
| `src/js/tools.utils.js` | `formatCurrency` now delegates to the locale-aware implementation and accepts both `(value, maxFrac)` and legacy `(value, currencyCode)` signatures. The production bundle and `.br`/`.gz` artifacts were rebuilt. |
| `templates/components/navbar.html` / `footer.html` / `tool_seo_macros.html` / `base.html` | Category labels, footer navigation, popular-tool names, legal links, breadcrumb/mobile-nav/cookie-banner ARIA labels, the shared methodology block and the helpful-feedback widget are localized through `tr()`/`category_label()`. The India-only SIP footer link is hidden for DE/ES/FR. |

Remaining rendered-UI blockers before adding hub surfaces:

- `templates/pages/tools.html` (the `/de/tools` and `/es/tools` directory) still
  renders English headings, FAQs, JSON-LD and filter chrome. The first release
  keeps `surfaces: []`, so the directory stays `noindex, follow`; localize it
  before adding the `tools` surface. It is part of the uncommitted
  homepage/tools redesign, so do not rewrite it blindly.
- **Wave-1a blog item hold:** keep `compound-interest-formula` at
  `translation_status: review` in the first release. `templates/blog/post.html`
  and `blog_macros.html` still render English post chrome (Published/Updated,
  min read, share, Key Takeaways, TOC, Related Guides, Methodology) and the post
  links India-only SIP/FD tools. Publishing it would expose English chrome on an
  indexed URL. Localize post chrome, filter related tools/guides, then re-review.
- `/de/blog`, the pillar hubs and post chrome are still English for the same
  reason; add `blog`/`blog_pillars` only after they are localized.
- A native reviewer must inspect the rendered DE/ES calculator pages on mobile
  and desktop, not only the YAML.

Run `python -m pytest tests/test_localized_calculator_ui.py -q` before release.
It fails if English chrome, `$`, US affordability terms, non-localized
defaults, or English footer/methodology/ARIA labels reappear.

## Inputs still required

| Input | Needed for | Status |
| --- | --- | --- |
| Native DE reviewer + YMYL finance credential | Sign-off on every DE pack | **Blocked** |
| Native ES (Spain) reviewer + YMYL finance credential | Sign-off on every ES pack | **Blocked** |
| GSC export for `storybrainai.com` (queries + pages, 16 months) | Real impressions/clicks/position | **Blocked** |
| Bing Webmaster export | Second demand source | **Blocked** |
| Paid keyword-tool export (Ahrefs/Semrush/DataForSEO) for DE and ES | Volume, difficulty, CPC | **Blocked** |
| Legal entity details | DE Impressum, ES Aviso legal | **Blocked** |
| Batch-1 approval and missing-tool decisions | Scope freeze | **Blocked** |
| DE/ES calculator UI localization | Native calculator chrome, EUR defaults and the DE/ES affordability model | **Done** (rendered regression tests pass) |
| DE/ES tools directory chrome | `/de/tools` and `/es/tools` still render English directory chrome; add `tools` only after localization | **Blocked** |
| DE/ES wave-1a blog post chrome | `post.html` / `blog_macros.html`; related-tool filtering | **Blocked** (blog stays `review`; release 8 tools first) |

Wave 1a drafting is complete. Do not start wave 1b or set any item to
`published` until the reviewer, data and UI inputs are available. The worksheet
can be filled incrementally, but `volume_status` must stay `TBD` until at least
two independent sources agree.

## Proposed URLs

Wave 1a is the first release candidate. Wave 1b follows only after 1a is live
and monitored for 28 days. Each locale gets four tools and one supporting
article per wave.

| Wave | DE target | ES target | Native angle |
| --- | --- | --- | --- |
| 1a | `/de/tool/emi-calculator` | `/es/tool/emi-calculator` | Kreditrechner / calculadora de préstamos; monthly rate, interest, amortization |
| 1a | `/de/tool/loan-affordability-calculator` | `/es/tool/loan-affordability-calculator` | Tragfähigkeit / capacidad de endeudamiento; income stress test |
| 1a | `/de/tool/mortgage-overpayment-calculator` | `/es/tool/mortgage-overpayment-calculator` | Sondertilgung / amortización anticipada; interest and term saved |
| 1a | `/de/tool/debt-calculator` | `/es/tool/debt-calculator` | Schulden abbauen / pagar deudas; payoff plan |
| 1a | `/de/blog/calculators/compound-interest-formula` | `/es/blog/calculators/compound-interest-formula` | Zinseszins Formel / fórmula del interés compuesto |
| 1b | `/de/tool/compound-calculator` | `/es/tool/compound-calculator` | Zinseszinsrechner / calculadora de interés compuesto |
| 1b | `/de/tool/credit-utilization-calculator` | `/es/tool/credit-utilization-calculator` | Kreditkarten-Auslastung / utilización del crédito |
| 1b | `/de/tool/savings-account-comparison-calculator` | `/es/tool/savings-account-comparison-calculator` | Tagesgeld / cuenta remunerada comparison |
| 1b | `/de/tool/retirement-planning-calculator` | `/es/tool/retirement-planning-calculator` | Rentenlücke / jubilación planning |
| 1b | `/de/blog/calculators/credit-utilization-30-rule` | `/es/blog/calculators/credit-utilization-30-rule` | 30% rule adapted to German Schufa / Spanish credit history |

The exact row-level keywords, audience, H1, internal links and content notes
are in the CSV. Slugs stay English in phase 1; only the copy and metadata are
localized.

## Excluded from this batch

- India-only tools for DE/ES/FR: `gst-calculator`, `eway-bill-calculator`,
  `sip-calculator`, `fd-calculator`, `job-card-generator`,
  `delivery-challan-generator`.
- India-centric blog posts: `emi-vs-sip-vs-fd-decision-guide` (SIP/FD/GST
  framing does not fit DE/ES). `emi-calculator-guide` is deferred because the
  EMI framing and slug do not match the native Kreditrechner/préstamo angle.
- English legal pages (`/about`, `/contact`, `/privacy`, `/terms`,
  `/disclaimer`). The code-level safety net blocks them even if the `static`
  surface is released.
- New tool gaps (VAT, severance, self-employed, mortgage, PDF
  compression/signing) until product scope is approved.

## Keyword research workflow

1. Export GSC queries and pages for the last 16 months. Filter to DE and ES
   properties and keep the query/page pair, not just the query.
2. Export Bing Webmaster queries and pages for the available period.
3. Export paid-tool data for Germany and Spain. Use exact-match volume,
   keyword difficulty and CPC in EUR; fill `paid_export_date` (and the GSC/Bing
   export dates) so the data can be re-validated later.
4. Fill the worksheet columns and set `data_source` to the sources actually
   used (for example `GSC+Bing+Ahrefs`). Do not overwrite the native seed
   terms; add validated variants in the same row or a child row with a new
   `batch_id`.
5. Set `volume_status` to `collected` when one source is filled, `validated`
   when at least two independent sources agree. Keep `TBD` otherwise.
6. Assign one primary keyword per URL. If two URLs compete for the same query,
   merge the intent or change the target before writing.
7. Re-check the proposed H1 against the primary keyword. The localized
   `seo_data.name` is the H1 source; do not rely on an English template
   literal.

The worksheet is intentionally empty in the GSC/Bing/paid columns. Do not
invent volumes, difficulty or CPC.

## Content pack requirements

Each released item must pass `scripts/quality_gate.py`:

- Tool: `about_body` >= 150 words, 5+ FAQs, every answer >= 12 words.
- Blog: `body_html` >= 800 words, 4+ H2, 4+ internal links, 5+ FAQs. The
  advisory targets are 1,100+ words and 8+ internal links; falling below them
  produces warnings, not errors.
- Native-language signal; no body identical to English or reused across
  locales; no `LSI:`, U+FFFD, TODO or template placeholders.
- Unique meta title and description; declared keywords present in the copy.
- Unique keyword sets per locale: no keyword may repeat across two tools or a
  tool and a post.
- `translation_status`, `reviewer`, `reviewed_at`, `author`, `sources`.
- YMYL packs need a native reviewer with finance credentials and authoritative
  sources (e.g. Bundesbank/Verbraucherzentrale for DE, Banco de España for ES).

Do not set `translation_status: published` before sign-off. A published item in
a quarantined locale is still `noindex`; the locale gate is independent.

Apply a pack surgically, then audit exactly its slugs:

```bash
# Dry run: validates the pack and prints the target items
python scripts/apply_content_pack.py data/content_packs/de_wave1a.yaml

# Apply (preserves CRLF and every unrelated byte)
python scripts/apply_content_pack.py data/content_packs/de_wave1a.yaml --write

# Batch gate: five items, no legacy overrides
python scripts/quality_gate.py --pack data/content_packs/de_wave1a.yaml
python scripts/quality_gate.py --pack data/content_packs/es_wave1a.yaml
```

The applier refuses to overwrite a `published` override unless
`--allow-published` is passed, and it verifies that only the target
`i18n.<locale>` block changed.

## Review and release sequence

1. **Keyword freeze**: data columns validated, one primary keyword per URL,
   worksheet approved.
2. **Draft**: native writer produces the pack; internal links point only to
   released or same-batch URLs.
3. **Native review**: reviewer checks language, claims, calculations and
   sources; fills `reviewer`, `reviewed_at`, `author`, `sources`.
4. **Item gate**: `python scripts/quality_gate.py --locale de --slug <slug>`
   and the ES equivalent. Fix errors before continuing.
5. **Batch gate**: `python scripts/quality_gate.py --pack
   data/content_packs/de_wave1a.yaml` (same for ES). All wave-1a items must
   pass; warnings should be reviewed, and `--strict` is preferred for YMYL
   pages. Do not use `--status review` alone; it selects every legacy override
   whose missing status defaults to `review`.
6. **UI gate**: run `python -m pytest tests/test_localized_calculator_ui.py -q`
   and render the four DE and four ES tool pages. Confirm there is no hardcoded
   English chrome, no US/India-only defaults, and no `$` output. `/de/tools` and
   `/es/tools` still render English directory chrome, so the first release
   excludes them via `surfaces: []` (they stay `noindex, follow`); do not add the
   `tools` surface until that page is localized. The calculator UI table above is
   the checklist. This gate is separate from the content gate and must be signed
   off by a native reviewer.
7. **Release**: set DE/ES to `published` in `data/locale_publication.yaml` with
   `surfaces: []` for the first deploy. The 8 wave-1a **tool** pages index from
   their own `translation_status`, so no English hub is exposed. Keep the
   wave-1a **blog** item at `translation_status: review`: `templates/blog/post.html`
   and `blog_macros.html` still render English post chrome (Published/Updated,
   min read, share, Key Takeaways, TOC, Related Guides, Methodology), and the
   post links India-only SIP/FD tools. Publishing it would expose English chrome
   on an indexed URL. Add `tools`, `blog` and `blog_pillars` only after
   `/de/tools`, `/de/blog`, the pillar hubs and the post chrome are localized;
   add `home`/`hubs` only after their chrome review. Leave `static` out until the
   legal pages are localized and the entity details are supplied.
8. **Deploy and verify**: check `X-Robots-Tag`, canonical, hreflang cluster,
   `sitemap-de.xml`/`sitemap-es.xml`, sitemap index and robots.txt. Submit the
   locale sitemaps in GSC and Bing; run IndexNow for released locales only.
9. **Monitor 28 days**: indexed count, impressions, queries, CTR, canonical
   selection and manual actions. Roll back by setting the locale to
   `quarantined` if quality or indexing regresses.

Wave 1b starts only after 1a has been live for 28 days and the query/page data
shows the native URL is being selected over the English one.

## Current baseline

```bash
# All 864 localized overrides, with blockers and readiness
python scripts/locale_backlog.py --csv var/locale-backlog.csv --json var/locale-backlog.json

# DE/ES only
python scripts/locale_backlog.py --locale de --locale es

# Released-locale gate (EN today; DE/ES join automatically when published)
python scripts/quality_gate.py --quiet
```

Current result: 10/864 items rebuilt and blocked only on
`missing_reviewer;missing_reviewed_at`; the other 854 are still blocked on
content, provenance or status. 0 ready, 0 released. That is expected until
native review, calculator UI localization and the data inputs are complete.
