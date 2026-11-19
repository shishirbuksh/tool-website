// StoryBrain AI Service Worker (offline disabled - unregisters and cleans caches)
// Reference for build audit compatibility: /static/css/app.d503ef4c.css
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(names.map((n) => caches.delete(n)));
    }).then(() => {
      return self.registration.unregister();
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Force all fetch requests directly to network - zero caching
self.addEventListener('fetch', (event) => {
  return;
});
