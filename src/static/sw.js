/**
 * SchemeSaathi PWA Service Worker
 * Cache Name: schemesaathi-shell-v1
 * Update Strategy:
 *  - Cache-First with network refresh for static app shell assets (HTML, CSS, JS, manifest, icons).
 *  - Network-First with graceful offline fallback for API endpoints (/api/).
 *  - Instant activation via skipWaiting() and clients.claim().
 *  - Clean cache pruning on activate to remove obsolete cache versions.
 */

const CACHE_NAME = "schemesaathi-shell-v1";
const SHELL_ASSETS = [
  "/",
  "/manifest.json",
  "/static/app.css",
  "/static/app.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-192.svg",
];

// 1. Install Phase: Cache App Shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        return cache.addAll(SHELL_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// 2. Activate Phase: Purge Old Caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => caches.delete(name))
        );
      })
      .then(() => self.clients.claim())
  );
});

// 3. Fetch Phase: Dynamic Routing
self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);

  // Non-GET requests (e.g. POST API calls) cannot be served from Cache API
  if (event.request.method !== "GET") {
    // For API POST requests that fail offline, provide a structured JSON response
    if (requestUrl.pathname.startsWith("/api/")) {
      event.respondWith(
        fetch(event.request).catch(() => {
          return new Response(
            JSON.stringify({
              error: "NetworkUnavailable",
              message: "Device is currently offline. Please reconnect to submit queries or evaluate rules.",
              is_offline: true,
            }),
            {
              status: 503,
              headers: { "Content-Type": "application/json" },
            }
          );
        })
      );
    }
    return;
  }

  // API GET calls: Network-first
  if (requestUrl.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          return response;
        })
        .catch(() => {
          return new Response(
            JSON.stringify({
              error: "NetworkUnavailable",
              message: "Device is currently offline. Cached data remains accessible locally.",
              is_offline: true,
            }),
            {
              status: 503,
              headers: { "Content-Type": "application/json" },
            }
          );
        })
    );
    return;
  }

  // App Shell & Static Assets: Cache-First with Network Fallback
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch in background to keep cache fresh
        fetch(event.request)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, networkResponse);
              });
            }
          })
          .catch(() => {
            // Offline - ignore background refresh failure
          });
        return cachedResponse;
      }

      // Not in cache: fetch from network and cache
      return fetch(event.request)
        .then((networkResponse) => {
          if (
            networkResponse &&
            networkResponse.status === 200 &&
            (event.request.url.startsWith(self.location.origin) ||
              event.request.mode === "navigate")
          ) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // If navigation fails offline, fallback to cached root shell
          if (event.request.mode === "navigate") {
            return caches.match("/");
          }
          return new Response("Network offline", { status: 503 });
        });
    })
  );
});
