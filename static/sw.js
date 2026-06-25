// StoryBrain AI Service Worker v1.0.1
const CACHE_NAME = 'storybrain-v29';
const STATIC_CACHE = 'storybrain-static-v27';

// Assets to pre-cache on install
const PRECACHE_URLS = [
  '/',
  '/static/css/app.css',
  '/static/favicon.svg',
  '/static/og-image.jpg',
  '/static/manifest.json',
  '/offline',
  '/static/js/app.js',
  '/static/js/tools.utils.js',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(PRECACHE_URLS);
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

  // Static assets: cache-first (CSS, JS, fonts, images)
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
        // Cache successful page responses
        if (response.status === 200) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
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

async function fetchAndCache(request) {
  try {
    const response = await fetch(request);
    if (response.status === 200) {
      const copy = response.clone();
      caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
    }
    return response;
  } catch (err) {
    return caches.match(request);
  }
}
