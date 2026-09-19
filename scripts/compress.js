const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

// ROUND-2 perf: emit precompressed .gz/.br for Caddy to serve directly.
// Targets mirror scripts/build.js outputs + postcss CSS output. No deps.
const targets = [
  'static/css/app.css',
  'static/css/fonts.css',
  'static/js/app.js',
  'static/js/tools.utils.js',
  'static/js/tools.js',
  'static/manifest.json',
  'static/sitemap.xsl',
];

function compressOne(rel) {
  const abs = path.join(__dirname, '..', rel);
  if (!fs.existsSync(abs)) {
    console.warn(`skip (missing): ${rel}`);
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
