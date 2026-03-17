"""PWA asset generation: manifest, service worker, and icon."""
from __future__ import annotations

import json


def generate_manifest(destination: str, dest_slug: str) -> str:
    """Generate a PWA manifest.json for the trip."""
    manifest = {
        "name": f"Vacationeer \u2014 {destination}",
        "short_name": destination,
        "start_url": f"./{dest_slug}-app.html",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1a2332",
        "icons": [
            {"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"},
        ],
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False)


def generate_service_worker(dest_slug: str) -> str:
    """Generate a service worker that caches the app shell and CDN assets."""
    return f"""\
const CACHE_NAME = 'vacationeer-{dest_slug}-v1';
const PRECACHE = [
  './{dest_slug}-app.html',
  './{dest_slug}-map.html',
  './manifest.json',
  './icon.svg',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js',
  'https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js',
];

self.addEventListener('install', function(e) {{
  e.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {{
      return cache.addAll(PRECACHE);
    }})
  );
  self.skipWaiting();
}});

self.addEventListener('activate', function(e) {{
  e.waitUntil(
    caches.keys().then(function(names) {{
      return Promise.all(
        names.filter(function(n) {{ return n !== CACHE_NAME; }})
             .map(function(n) {{ return caches.delete(n); }})
      );
    }})
  );
  self.clients.claim();
}});

self.addEventListener('fetch', function(e) {{
  var url = e.request.url;
  // Network-first for API calls
  if (url.includes('/api/')) {{
    e.respondWith(
      fetch(e.request).catch(function() {{
        return new Response(JSON.stringify({{error: 'offline'}}), {{
          status: 503,
          headers: {{'Content-Type': 'application/json'}}
        }});
      }})
    );
    return;
  }}
  // Cache-first for everything else
  e.respondWith(
    caches.match(e.request).then(function(cached) {{
      return cached || fetch(e.request).then(function(resp) {{
        if (resp.ok) {{
          var clone = resp.clone();
          caches.open(CACHE_NAME).then(function(cache) {{
            cache.put(e.request, clone);
          }});
        }}
        return resp;
      }});
    }})
  );
}});
"""


def generate_icon_svg(letter: str, color: str = "#1a2332") -> str:
    """Generate a simple SVG icon with a colored circle and letter."""
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="96" fill="{color}"/>
  <text x="256" y="340" text-anchor="middle"
        font-family="system-ui,sans-serif" font-size="300" font-weight="700"
        fill="#ffffff">{letter.upper()}</text>
</svg>
"""


def generate_index_redirect(dest_slug: str) -> str:
    """Generate a minimal index.html that redirects to the app."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta http-equiv="refresh" content="0;url=./{dest_slug}-app.html"></head>
<body><a href="./{dest_slug}-app.html">Open Vacationeer</a></body>
</html>
"""
