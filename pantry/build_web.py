#!/usr/bin/env python3
"""Build the installable (Home Screen) version of the pantry app into pantry/web/.

pantry/index.html is the single source: a page fragment (it is also published as a
claude.ai artifact). This wraps it in a full HTML document with app metadata, adds a
web app manifest, an offline service worker and the app icons.

Usage: python3 pantry/build_web.py   (icons need Playwright's Chromium; skipped if missing)
"""
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / 'index.html'
OUT = ROOT / 'web'

APP_NAME = 'Pantry'
BG_LIGHT, BG_DARK = '#f0e4cf', '#1c140e'
BROWN, MUSTARD, CREAM = '#74461f', '#d9a62e', '#fff3dc'

ICON_SVG = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="{BROWN}"/>
  <rect x="37" y="19" width="26" height="9" rx="3" fill="{MUSTARD}"/>
  <rect x="27" y="31" width="46" height="50" rx="12" fill="none" stroke="{CREAM}" stroke-width="4"/>
  <rect x="32" y="52" width="36" height="24" rx="7" fill="{MUSTARD}"/>
</svg>'''

HEAD = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{APP_NAME}">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="{BG_LIGHT}" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="{BG_DARK}" media="(prefers-color-scheme: dark)">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icons/icon-180.png">
<link rel="icon" type="image/png" href="/icons/icon-192.png">
<style>:root {{ padding-top: env(safe-area-inset-top, 0px); }} body {{ margin: 0; }} img {{ max-width: 100%; }}</style>
'''

SW_REGISTER = '''<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}));
}
</script>
'''

SERVICE_WORKER = '''// Offline cache for the pantry app. CACHE changes on every build so old files are dropped.
const CACHE = 'pantry-__VERSION__';
const SHELL = ['/', '/manifest.webmanifest', '/icons/icon-180.png', '/icons/icon-192.png', '/icons/icon-512.png'];
const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // The page itself: try the network first so updates arrive, fall back to the cached copy offline
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req)
      .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put('/', copy)); return res; })
      .catch(() => caches.match('/')));
    return;
  }

  // Fonts: serve from cache, refresh in the background
  if (FONT_HOSTS.includes(url.hostname)) {
    e.respondWith(caches.open(CACHE).then(async (c) => {
      const hit = await c.match(req);
      const fresh = fetch(req).then((res) => { c.put(req, res.clone()); return res; }).catch(() => hit);
      return hit || fresh;
    }));
    return;
  }

  // Own files (icons, manifest): cache first
  if (url.origin === location.origin) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
  }
});
'''


def build_page() -> str:
    src = SRC.read_text(encoding='utf-8')
    split = src.index('</style>') + len('</style>')
    head_part = src[:split].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
    body_part = src[split:]
    return HEAD + head_part + '\n</head>\n<body>' + body_part + SW_REGISTER + '</body>\n</html>\n'


def build_icons() -> None:
    icons = OUT / 'icons'
    icons.mkdir(parents=True, exist_ok=True)
    (icons / 'icon.svg').write_text(ICON_SVG, encoding='utf-8')
    script = f'''
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch();
  for (const size of [180, 192, 512]) {{
    const p = await b.newPage({{ viewport: {{ width: size, height: size }} }});
    await p.setContent(`<style>html,body{{margin:0}}svg{{display:block;width:${{size}}px;height:${{size}}px}}</style>{ICON_SVG}`);
    await p.screenshot({{ path: '{icons}/icon-' + size + '.png' }});
    await p.close();
  }}
  await b.close();
}})();'''
    try:
        subprocess.run(['node', '-e', script], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print('Icons not rendered (needs node + Playwright); existing PNGs kept.')


def main() -> None:
    OUT.mkdir(exist_ok=True)
    page = build_page()
    (OUT / 'index.html').write_text(page, encoding='utf-8')
    version = hashlib.sha1(page.encode()).hexdigest()[:10]
    (OUT / 'sw.js').write_text(SERVICE_WORKER.replace('__VERSION__', version), encoding='utf-8')
    manifest = {
        'name': 'Home Pantry', 'short_name': APP_NAME, 'start_url': '/', 'scope': '/', 'display': 'standalone',
        'background_color': BG_LIGHT, 'theme_color': BG_LIGHT,
        'icons': [
            {'src': '/icons/icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
            {'src': '/icons/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
        ],
    }
    (OUT / 'manifest.webmanifest').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    build_icons()
    print(f'Built {OUT} (cache version {version})')


if __name__ == '__main__':
    main()
