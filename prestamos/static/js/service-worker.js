const CACHE_NAME = "prestamos-cache-v3"; // versión nueva
const urlsToCache = [
  "/", // página principal
  "/static/manifest.json",
  "/static/icons/icon-loans-192x192-v3.png",
  "/static/icons/icon-loans-512x512-v3.png",
  "/static/css/style.css",
  "/static/js/app.js"
];

// Instalar y guardar archivos en caché
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        // Validamos que todos los recursos existan
        return Promise.all(
          urlsToCache.map((url) =>
            fetch(url)
              .then((response) => {
                if (!response.ok) {
                  console.warn("No se pudo cargar:", url);
                  return;
                }
                return cache.put(url, response.clone());
              })
              .catch(() => console.warn("Error al obtener:", url))
          )
        );
      })
      .then(() => self.skipWaiting())
  );
});

// Activar y limpiar cachés antiguas
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log("Eliminando caché vieja:", cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Interceptar solicitudes y servir desde caché o red
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      if (response) return response;

      return fetch(event.request)
        .then((networkResponse) => {
          if (!networkResponse || networkResponse.status !== 200) {
            return networkResponse;
          }

          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });

          return networkResponse;
        })
        .catch(() => {
          // Página offline opcional
          return caches.match("/static/offline.html");
        });
    })
  );
});
