import re, os, sys, json, ssl, urllib.request, urllib.parse, collections
OUT = sys.argv[1]
os.makedirs(OUT + '/html', exist_ok=True)
ctx = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
opener = urllib.request.build_opener(NoRedir, urllib.request.HTTPSHandler(context=ctx), urllib.request.ProxyHandler())
HOSTS = ('hipelpools.ca', 'blog.hipelpools.ca')
SKIP = re.compile(r'\.(css|js|png|jpe?g|webp|gif|pdf|svg|ico|xml|mp4|mov|zip|docx?)$', re.I)
def norm(base, href):
    href = href.replace('&amp;', '&').strip()
    if href.startswith(('mailto:', 'tel:', 'javascript:', '#')): return None
    u = urllib.parse.urljoin(base, href)
    p = urllib.parse.urlsplit(u)
    host = p.hostname or ''
    if host == 'www.hipelpools.ca': host = 'hipelpools.ca'
    if host not in HOSTS: return None
    path = p.path or '/'
    if SKIP.search(path) or path.startswith(('/hubfs', '/hs-fs', '/_hcms', '/hs/', '/hs-search', '/cs/', '/__')): return None
    return f'https://{host}{path}'
seeds = [l.strip() for f in sys.argv[2:] for l in open(f) if l.strip()]
q = collections.deque(); seen = set()
for s in seeds:
    n = norm(s, s)
    if n and n not in seen: seen.add(n); q.append(n)
results = {}
while q:
    u = q.popleft()
    try:
        r = opener.open(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 site-migration'}), timeout=30)
        code, body, loc = r.status, r.read().decode('utf-8', 'replace'), None
    except urllib.error.HTTPError as e:
        code, body, loc = e.code, '', e.headers.get('Location')
    except Exception as e:
        code, body, loc = 0, '', str(e)
    results[u] = {'status': code, 'location': loc}
    links = []
    if code == 200:
        fn = OUT + '/html/' + re.sub(r'[^a-zA-Z0-9._-]', '_', u[8:]) + '.html'
        open(fn, 'w').write(body); results[u]['file'] = fn
        links = re.findall(r'href="([^"]+)"', body)
    elif loc:
        links = [loc]
    for h in links:
        n = norm(u, h)
        if n and n not in seen: seen.add(n); q.append(n)
    print(code, u, loc or '', file=sys.stderr)
json.dump(results, open(OUT + '/crawl.json', 'w'), indent=1)
c = collections.Counter(v['status'] for v in results.values()); print(dict(c))
