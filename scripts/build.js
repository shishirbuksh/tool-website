const esbuild = require('esbuild');
const isProd = process.env.NODE_ENV === 'production';

// TODO(hash): emit content-hashed filenames (e.g. app.[hash].js) so Caddy can
// safely use `immutable` long cache; non-hashed outputs must use must-revalidate.
async function build() {
  const makeBundle = (entry, outfile) =>
    esbuild.build({
      entryPoints: [entry],
      outfile,
      bundle: true,
      minify: isProd,
      sourcemap: !isProd ? 'inline' : false,
      format: 'iife',
      target: ['es2020', 'chrome80', 'firefox80', 'safari14'],
    });

  // Build each JS file individually
  // tools.utils.js must remain separate since it defines window.sbr.*
  // that individual tool pages rely on
  await Promise.all([
    makeBundle('src/js/app.js', 'static/js/app.js'),
    makeBundle('src/js/tools.utils.js', 'static/js/tools.utils.js'),
    makeBundle('src/js/tools.js', 'static/js/tools.js'),
  ]);
}

build().catch((err) => {
  console.error('build failed:', err && err.message ? err.message : err);
  if (err && err.stack) console.error(err.stack);
  process.exit(1);
});
