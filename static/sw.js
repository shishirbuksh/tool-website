// StoryBrain AI Service Worker v38 (keep in sync with CACHE_NAME / STATIC_CACHE below)
const CACHE_NAME = 'storybrain-v38';
const STATIC_CACHE = 'storybrain-static-v38';
const PAGE_CACHE_MAX_ENTRIES = 50;

// Assets to pre-cache on install (app-shell only; OG/screenshots lazy via runtime cache)
const PRECACHE_URLS = [
  '/',
  '/static/css/app.css',
  '/static/css/fonts.css',
  '/static/favicon.svg',
  '/static/favicon.ico',
  '/static/apple-touch-icon.png',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/manifest.json',
  '/offline',
  '/static/js/app.js',
  '/static/js/tools.utils.js',
  '/static/js/tools.js',
  // NOTE: qrcode.min.js + jsqr.min.js intentionally NOT precached (large vendor
  // bundles) — they are cached lazily on first use via fetchAndCache below.
];

// Install: cache static assets (per-URL so one 404 doesn't fail the whole install)
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return Promise.allSettled(
        PRECACHE_URLS.map((url) => cache.add(url).catch((err) => {
          console.warn('[sw] precache failed:', url, err);
        }))
      );
    }).then(() => {
      self.skipWaiting();
    })
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => {
      self.clients.claim();
    })
  );
});

// Listen for skipWaiting message from the client page
self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
});

// Fetch: network-first for pages, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests and non-http protocols
  if (request.method !== 'GET') return;
  if (!url.protocol.startsWith('http')) return;

  // Skip cross-origin requests (CDN fonts, external APIs, etc.)
  if (url.origin !== location.origin) return;

  // Static assets: cache-first (CSS, JS, fonts, images).
  // NOTE: app.css/js carry ?v=<app_version> query strings — match EXACTLY
  // (no ignoreSearch) so a cached v1 can never serve a v2 URL. Each versioned
  // URL caches under its own full key; old caches are purged on activate.
  if (
    url.pathname.startsWith('/static/') ||
    url.pathname === '/favicon.ico'
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetchAndCache(request);
      })
    );
    return;
  }

  // API calls: network-only
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request).catch(() => {
      return new Response(JSON.stringify({ error: 'You are offline' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      });
    }));
    return;
  }

  // Pages: network-first (fallback to cache, then offline page)
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful page responses (LRU-capped to avoid unbounded growth)
        if (response.status === 200) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, copy).then(() => trimPageCache(cache)).catch(() => {});
          }).catch(() => {});
        }
        return response;
      })
      .catch(() => {
        return caches.match(request).then((cached) => {
          return cached || caches.match('/offline');
        });
      })
  );
});

// LRU cap: keep at most PAGE_CACHE_MAX_ENTRIES page responses, evict oldest first.
async function trimPageCache(cache) {
  try {
    const keys = await cache.keys();
    if (keys.length > PAGE_CACHE_MAX_ENTRIES) {
      await cache.delete(keys[0]);
      // Recurse in case multiple puts raced past the cap.
      return trimPageCache(cache);
    }
  } catch (err) {
    // Cache trim is best-effort; never break page serving.
  }
}

async function fetchAndCache(request) {
  try {
    const response = await fetch(request);
    if (response.status === 200) {
      const copy = response.clone();
      caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
    }
    return response;
  } catch (err) {
    return caches.match(request);
  }
}
