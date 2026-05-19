// Biblioteca Psi Real — Service Worker
// Versão: incrementar ao fazer deploy para forçar atualização de cache

const CACHE_VERSION = 'bpr-v2';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGES_CACHE  = `${CACHE_VERSION}-pages`;

// Recursos essenciais cacheados na instalação
const PRECACHE_URLS = [
  '/psireal-hub/biblioteca-tcc/',
  '/psireal-hub/biblioteca-tcc/index.html',
  '/psireal-hub/biblioteca-tcc/materiais/persons-formulacao-caso/index.html',
  '/psireal-hub/biblioteca-tcc/materiais/avaliacao-tcc/index.html',
  '/psireal-hub/biblioteca-tcc/materiais/reestruturacao-cognitiva/index.html',
  '/psireal-hub/biblioteca-tcc/materiais/exposicao-epr/index.html',
  '/psireal-hub/biblioteca-tcc/materiais/alianca-terapeutica/index.html',
  '/psireal-hub/biblioteca-tcc/manifest.json',
  '/psireal-hub/biblioteca-tcc/icons/icon-192.png',
  '/psireal-hub/biblioteca-tcc/icons/icon-512.png',
];

// ─── INSTALL ──────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(PRECACHE_URLS);
    }).then(() => self.skipWaiting())
  );
});

// ─── ACTIVATE ─────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('bpr-') && name !== STATIC_CACHE && name !== PAGES_CACHE)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// ─── FETCH ────────────────────────────────────────────────────────────────────
// Estratégia: Cache First para assets, Network First para HTML
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorar requisições não-http e cross-origin
  if (!url.protocol.startsWith('http') || url.origin !== location.origin) return;

  // HTML: Network First (conteúdo atualizado), fallback para cache
  if (request.headers.get('Accept')?.includes('text/html')) {
    event.respondWith(networkFirstHtml(request));
    return;
  }

  // Outros assets: Cache First
  event.respondWith(cacheFirst(request));
});

async function networkFirstHtml(request) {
  const cache = await caches.open(STATIC_CACHE);
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch {
    const cached = await cache.match(request);
    return cached || offlineFallback();
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch {
    return new Response('Sem conexão', { status: 503, statusText: 'Offline' });
  }
}

function offlineFallback() {
  return new Response(`
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Offline — Biblioteca Psi Real</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, sans-serif;
      background: #FAFAFA; color: #2A1A18;
      min-height: 100vh; display: flex;
      align-items: center; justify-content: center;
      text-align: center; padding: 2rem;
    }
    .wrap { max-width: 400px; }
    .icon {
      width: 64px; height: 64px; background: #F8EDEB;
      border-radius: 16px; margin: 0 auto 1.5rem;
      display: flex; align-items: center; justify-content: center;
    }
    h1 { font-size: 22px; font-weight: 500; margin-bottom: 0.5rem; }
    p { font-size: 14px; color: #8A7370; line-height: 1.7; margin-bottom: 1.5rem; }
    a {
      display: inline-block;
      background: #8B4A52; color: #fff; text-decoration: none;
      padding: 10px 22px; border-radius: 8px; font-size: 14px; font-weight: 500;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="icon">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#8B4A52" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M1 6s4-2 11-2 11 2 11 2v13s-4-2-11-2S1 19 1 19z"/>
        <line x1="12" y1="4" x2="12" y2="17"/>
      </svg>
    </div>
    <h1>Você está offline</h1>
    <p>Sem conexão com a internet. As páginas já visitadas estão disponíveis no cache do dispositivo.</p>
    <a href="/">← Voltar ao início</a>
  </div>
</body>
</html>
  `, {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8' }
  });
}
