/* Chair Library offline helper.
   Keeps the website on the phone so it opens inside a shop with no signal.
   Bump CACHE when the shell files change. */
'use strict';

const CACHE = 'chair-library-v1';

/* The pages and icons the site needs to open at all. */
const SHELL = [
  './',
  './index.html',
  './Chair Website.html',
  './manifest.webmanifest',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      /* One bad URL must not kill the whole install, so add them one by one. */
      .then((cache) => Promise.all(SHELL.map((url) => cache.add(url).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isPhoto(request) {
  return request.destination === 'image' || /\.(jpg|jpeg|png|webp|gif|svg)$/i.test(new URL(request.url).pathname);
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  /* Photos: show the saved copy at once, then quietly refresh it. */
  if (isPhoto(request)) {
    event.respondWith(
      caches.match(request).then((hit) => {
        const update = fetch(request).then((response) => {
          if (response && (response.ok || response.type === 'opaque')) {
            caches.open(CACHE).then((cache) => cache.put(request, response.clone()));
          }
          return response;
        }).catch(() => hit);
        return hit || update;
      })
    );
    return;
  }

  /* Pages: try the network first so a rebuilt website shows up, fall back to the saved copy. */
  event.respondWith(
    fetch(request).then((response) => {
      if (response && response.ok && new URL(request.url).origin === self.location.origin) {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copy));
      }
      return response;
    }).catch(() => caches.match(request, { ignoreSearch: true })
      .then((hit) => hit || caches.match('./Chair Website.html')))
  );
});

/* The page can ask for every photo to be saved before a shop visit. */
self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type !== 'save-photos' || !Array.isArray(data.urls)) return;
  const reply = (payload) => {
    if (event.source) event.source.postMessage(payload);
  };
  caches.open(CACHE).then(async (cache) => {
    let done = 0;
    let failed = 0;
    for (const url of data.urls) {
      try {
        const hit = await cache.match(url);
        if (hit) { done += 1; continue; }
        const response = await fetch(url, /^https?:\/\//.test(url) && !url.startsWith(self.location.origin) ? { mode: 'no-cors' } : undefined);
        if (response && (response.ok || response.type === 'opaque')) {
          await cache.put(url, response.clone());
          done += 1;
        } else {
          failed += 1;
        }
      } catch (e) {
        failed += 1;
      }
      if ((done + failed) % 10 === 0) reply({ type: 'save-photos-progress', done, failed, total: data.urls.length });
    }
    reply({ type: 'save-photos-done', done, failed, total: data.urls.length });
  });
});
