const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

// Emit a content-hashed copy of static/css/app.css so reverse proxies (CloudPanel Nginx,
// Cloudflare) can never serve a stale precompressed app.css.br under query-string URLs,
// and emit precompressed .gz/.br for Caddy/Nginx to serve directly. No external deps.
const ROOT = path.join(__dirname, '..');
const HASHED_CSS_RE = /^app\.[0-9a-f]{8}\.css(\.(?:gz|br))?$/i;

function syncHashedAppCss() {
  const cssDir = path.join(ROOT, 'static', 'css');
  const appCssAbs = path.join(cssDir, 'app.css');
  if (!fs.existsSync(appCssAbs)) return null;

  const buf = fs.readFileSync(appCssAbs);
  const hash8 = crypto.createHash('sha256').update(buf).digest('hex').slice(0, 8);
  const hashedName = `app.${hash8}.css`;
  const hashedAbs = path.join(cssDir, hashedName);

  for (const entry of fs.readdirSync(cssDir)) {
    if (!HASHED_CSS_RE.test(entry)) continue;
    if (entry === hashedName || entry === `${hashedName}.gz` || entry === `${hashedName}.br`) continue;
    fs.unlinkSync(path.join(cssDir, entry));
  }

  if (!fs.existsSync(hashedAbs) || !fs.readFileSync(hashedAbs).equals(buf)) {
    fs.writeFileSync(hashedAbs, buf);
    console.log(`emitted: static/css/${hashedName} (${buf.length} bytes)`);
  }
  syncServiceWorker(hashedName);
  return `static/css/${hashedName}`;
}

function syncServiceWorker(hashedCssName) {
  const swAbs = path.join(ROOT, 'static', 'sw.js');
  if (!fs.existsSync(swAbs)) return;

  const h = crypto.createHash('sha256');
  for (const rel of [
    `static/css/${hashedCssName}`,
    'static/css/fonts.css',
    'static/js/app.js',
    'static/js/tools.utils.js',
    'static/js/tools.js',
  ]) {
    const abs = path.join(ROOT, rel);
    if (fs.existsSync(abs)) h.update(fs.readFileSync(abs));
  }
  const swHash = h.digest('hex').slice(0, 8);

  const orig = fs.readFileSync(swAbs, 'utf8');
  let next = orig
    .replace(
      /\/static\/css\/app(?:\.[0-9a-f]{8})?\.css/gi,
      `/static/css/${hashedCssName}`,
    )
    .replace(
      /const CACHE_NAME = 'storybrain-[^']+';/,
      `const CACHE_NAME = 'storybrain-v47-${swHash}';`,
    )
    .replace(
      /const STATIC_CACHE = 'storybrain-static-[^']+';/,
      `const STATIC_CACHE = 'storybrain-static-v47-${swHash}';`,
    );

  if (next !== orig) {
    fs.writeFileSync(swAbs, next, 'utf8');
    console.log(`synced: static/sw.js (css=${hashedCssName}, sw=${swHash})`);
  }
}

const hashedCssTarget = syncHashedAppCss();

const targets = [
  'static/css/app.css',
  ...(hashedCssTarget ? [hashedCssTarget] : []),
  'static/css/fonts.css',
  'static/js/app.js',
  'static/js/tools.utils.js',
  'static/js/tools.js',
  'static/js/qrcode.min.js',
  'static/js/jsqr.min.js',
  'static/js/vendor/apexcharts.min.js',
  'static/js/vendor/chart.min.js',
  'static/sw.js',
  'static/data/thesaurus.json',
  'static/manifest.json',
  'static/sitemap.xsl',
];

function compressOne(rel) {
  const abs = path.join(ROOT, rel);
  if (!fs.existsSync(abs)) {
    // Silently skip optional missing targets (e.g. fonts.css/sitemap.xsl not
    // built yet) to avoid CI noise; use VERBOSE=1 to debug.
    if (process.env.VERBOSE) console.debug(`skip (missing): ${rel}`);
    return;
  }
  const buf = fs.readFileSync(abs);
  // .gz
  const gz = zlib.gzipSync(buf, { level: 9 });
  fs.writeFileSync(abs + '.gz', gz);
  // .br (brotli, quality 11)
  const br = zlib.brotliCompressSync(buf, {
    params: { [zlib.constants.BROTLI_PARAM_QUALITY]: 11 },
  });
  fs.writeFileSync(abs + '.br', br);
  console.log(`compressed: ${rel} (${buf.length} -> gz ${gz.length}, br ${br.length})`);
}

for (const t of targets) {
  try {
    compressOne(t);
  } catch (err) {
    console.error(`failed: ${t}`, err);
    process.exitCode = 1;
  }
}
