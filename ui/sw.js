/**
 * MSA AI Agent — Service Worker
 * Provides offline support + instant loading for the PWA.
 *
 * Strategy:
 *   - App shell (HTML/CSS/JS)  → Cache-first with background update
 *   - API endpoints (/api/*)   → Network-only (always fresh)
 *   - SocketIO (/socket.io/*) → Network-only (real-time)
 *   - Fonts / CDN assets       → Cache-first
 */

const CACHE_VERSION = 'msa-v2.2';
const SHELL_CACHE   = `${CACHE_VERSION}-shell`;
const CDN_CACHE     = `${CACHE_VERSION}-cdn`;

const SHELL_ASSETS = [
  '/app',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/socket.io.min.js',
];

// FIX ISSUE-5: socket.io is now served locally — only Google Fonts remain as CDN asset
const CDN_ASSETS = [
  'https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700&display=swap',
];

// ── INSTALL: Pre-cache app shell ─────────────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Installing MSA Agent v2.1…');
  event.waitUntil(
    Promise.all([
      caches.open(SHELL_CACHE).then((cache) => {
        return cache.addAll(SHELL_ASSETS).catch((err) => {
          console.warn('[SW] Shell pre-cache partial failure:', err);
        });
      }),
      caches.open(CDN_CACHE).then((cache) => {
        return cache.addAll(CDN_ASSETS).catch((err) => {
          console.warn('[SW] CDN pre-cache partial failure:', err);
        });
      }),
    ])
  );
  self.skipWaiting();
});

// ── ACTIVATE: Clean up old caches ───────────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating MSA Agent v2.1…');
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== CDN_CACHE)
          .map((k) => {
            console.log('[SW] Deleting old cache:', k);
            return caches.delete(k);
          })
      )
    )
  );
  self.clients.claim();
});

// ── FETCH: Intercept requests ────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and browser-extension requests
  if (request.method !== 'GET') return;
  if (!url.protocol.startsWith('http')) return;

  // NETWORK-ONLY: API calls, SocketIO, socket.io polling
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/socket.io/') ||
    url.pathname.startsWith('/mobile/api/')
  ) {
    return; // Let browser handle it natively
  }

  // CDN assets — cache-first
  if (CDN_ASSETS.some((cdnUrl) => request.url.startsWith(cdnUrl.split('?')[0]))) {
    event.respondWith(
      caches.open(CDN_CACHE).then((cache) =>
        cache.match(request).then((cached) => {
          if (cached) return cached;
          return fetch(request).then((response) => {
            cache.put(request, response.clone());
            return response;
          });
        })
      )
    );
    return;
  }

  // App shell — network-first with cache fallback
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.status === 200) {
          caches.open(SHELL_CACHE).then((cache) => {
            cache.put(request, response.clone());
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(request).then((cached) => {
          if (cached) return cached;
          // Offline fallback for navigation
          if (request.mode === 'navigate') {
            return caches.match('/app');
          }
          return new Response(
            JSON.stringify({ status: 'error', message: 'Offline — no cached response.' }),
            {
              status: 503,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        });
      })
  );
});

// ── PUSH NOTIFICATIONS (future) ──────────────────────────────────────────────
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'MSA AI Agent';
  const options = {
    body: data.body || 'New notification from MSA.',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    vibrate: [100, 50, 100],
    data: { url: data.url || '/app' },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/app'));
});
