const SHELL_CACHE = "libraryos-shell-v1";
const PRECACHE_URLS = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icons/icon.svg",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/offline.html",
];

function isProtectedEndpoint(pathname) {
  return pathname === "/api"
    || pathname.startsWith("/api/")
    || pathname === "/public-api"
    || pathname.startsWith("/public-api/");
}

function isCacheableAsset(request, url) {
  return ["script", "style", "image", "font"].includes(request.destination)
    || url.pathname.startsWith("/icons/")
    || url.pathname === "/manifest.webmanifest";
}

async function precacheShell(cache) {
  await cache.addAll(PRECACHE_URLS);
  const indexResponse = await cache.match("/index.html");
  if (!indexResponse) return;
  const html = await indexResponse.text();
  const assetUrls = [...html.matchAll(/(?:src|href)=["'](\/assets\/[^"']+)["']/g)].map((match) => match[1]);
  await cache.addAll([...new Set(assetUrls)]);
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(precacheShell)
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== SHELL_CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || isProtectedEndpoint(url.pathname)) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.put("/index.html", response.clone())));
          }
          return response;
        })
        .catch(async () => {
          const cache = await caches.open(SHELL_CACHE);
          return (await cache.match("/index.html")) ?? (await cache.match("/offline.html"));
        }),
    );
    return;
  }

  if (!isCacheableAsset(request, url)) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          if (response.ok) {
            event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.put(request, response.clone())));
          }
          return response;
        })
        .catch(() => Response.error());
    }),
  );
});
