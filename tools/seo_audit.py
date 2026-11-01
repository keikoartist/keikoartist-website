"""SEO audit for keikoartist.com (run by .github/workflows/seo-audit.yml).
Probes given URLs and crawls every internal link reachable from the sitemap + homepage.
Reports status codes, redirects, titles, H1s, canonicals, robots directives, broken links and duplicates."""
import re, sys, json, urllib.request, urllib.error, urllib.parse, html
BASE = sys.argv[1] if len(sys.argv) > 1 else 'https://keikoartist.com/'
UA = 'Mozilla/5.0 (compatible; KeikoArts-SEO-audit/1.0; +https://keikoartist.com/)'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
opener = urllib.request.build_opener(NoRedirect)
def fetch(url, method='GET'):
    req = urllib.request.Request(url, method=method, headers={'User-Agent': UA})
    try:
        r = opener.open(req, timeout=30); body = r.read() if method == 'GET' else b''
        return r.status, dict(r.headers), body
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), (e.read() if method == 'GET' else b'')
    except Exception as e:
        return 0, {}, str(e).encode()
def meta(body):
    t = body.decode('utf-8', 'replace')
    g = lambda p: (re.search(p, t, re.I | re.S) or [None, None])[1]
    h1s = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<h1[^>]*>(.*?)</h1>', t, re.I | re.S)]
    return {'title': html.unescape(g(r'<title>(.*?)</title>') or ''), 'desc': html.unescape(g(r'<meta name="description" content="([^"]*)"') or ''),
            'canonical': g(r'<link rel="canonical" href="([^"]*)"'), 'robots': g(r'<meta name="robots" content="([^"]*)"'),
            'h1': [html.unescape(h) for h in h1s], 'ld': len(re.findall(r'application/ld\+json', t)),
            'imgs_no_alt': len([i for i in re.findall(r'<img\b[^>]*>', t, re.I) if not re.search(r'\balt="[^"]+"', i)]),
            'links': re.findall(r'(?:href|src|poster)="([^"#]+)', t)}
mode = sys.argv[2] if len(sys.argv) > 2 else 'crawl'
if mode == 'probe':
    for p in sys.argv[3:]:
        st, hd, body = fetch(urllib.parse.urljoin(BASE, p))
        m = meta(body) if 'html' in hd.get('Content-Type', '') else {}
        print(f"{st:>3} {p:<32} -> {hd.get('Location','')} | {hd.get('Content-Type','')[:24]} | title: {m.get('title','')[:70]!r} | x-robots: {hd.get('X-Robots-Tag','')}")
    sys.exit(0)
# crawl
st, hd, sm = fetch(urllib.parse.urljoin(BASE, 'sitemap.xml'))
locs = re.findall(r'<loc>(.*?)</loc>', sm.decode('utf-8', 'replace'))
print(f'sitemap.xml: HTTP {st}, {len(locs)} URLs')
st, hd, rb = fetch(urllib.parse.urljoin(BASE, 'robots.txt')); print(f'robots.txt: HTTP {st}\n' + rb.decode('utf-8', 'replace'))
host = urllib.parse.urlparse(BASE).netloc
todo = list(dict.fromkeys(locs + [BASE])); seen = {}; pages = {}; problems = []
while todo:
    u = todo.pop(0)
    if u in seen: continue
    st, hd, body = fetch(u); seen[u] = st
    if st in (301, 302, 307, 308): problems.append(f'REDIRECT {u} -> {hd.get("Location")}')
    if st != 200: problems.append(f'HTTP {st}: {u}'); continue
    if 'text/html' not in hd.get('Content-Type', ''): continue
    m = meta(body); pages[u] = m
    for l in m['links']:
        a = urllib.parse.urljoin(u, html.unescape(l)).split('#')[0]
        pu = urllib.parse.urlparse(a)
        if pu.scheme not in ('http', 'https') or pu.netloc != host: continue
        if any(x in pu.path for x in ('order-api.php', 'chat-api.php', 'notify-discord.php')): continue
        if pu.path.endswith(('.webp', '.png', '.jpg', '.mp4', '.svg', '.css', '.js', '.ico', '.xml', '.txt')):
            if a not in seen:
                s2, h2, _ = fetch(a, 'HEAD'); seen[a] = s2
                if s2 != 200: problems.append(f'HTTP {s2}: {a} (linked from {u})')
            continue
        if a not in seen and a not in todo: todo.append(a)
titles = {}; h1s = {}
for u, m in pages.items():
    print(f"\nPAGE {u}\n  title ({len(m['title'])}): {m['title']}\n  desc ({len(m['desc'])}): {m['desc']}\n  h1: {m['h1']}\n  canonical: {m['canonical']} | robots: {m['robots']} | json-ld blocks: {m['ld']} | <img> without alt: {m['imgs_no_alt']}")
    titles.setdefault(m['title'], []).append(u); h1s.setdefault(' / '.join(m['h1']), []).append(u)
    if len(m['h1']) != 1: problems.append(f'{u}: {len(m["h1"])} H1 headings')
    if m['canonical'] != u and not (u == BASE and m['canonical'] == BASE): problems.append(f'{u}: canonical is {m["canonical"]}')
    if m['robots'] and 'noindex' in m['robots']: problems.append(f'{u}: noindex')
    if m['imgs_no_alt']: problems.append(f'{u}: {m["imgs_no_alt"]} images without alt')
    if u not in locs: problems.append(f'{u}: not in sitemap')
for t, us in titles.items():
    if len(us) > 1: problems.append(f'Duplicate title {t!r}: {us}')
for t, us in h1s.items():
    if len(us) > 1: problems.append(f'Duplicate H1 {t!r}: {us}')
for l in locs:
    if seen.get(l) != 200: problems.append(f'sitemap URL not 200: {l} ({seen.get(l)})')
print(f'\nCrawled {len(pages)} pages, {len(seen)} URLs checked.')
print('PROBLEMS:' if problems else 'PROBLEMS: none'); [print('  - ' + p) for p in problems]
