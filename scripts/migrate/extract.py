#!/usr/bin/env python3
"""
One-time HubSpot -> static site content extractor for hipelpools.ca.

Reads the crawl produced by crawl.py (html files + crawl.json) and writes:

  src/content/pages/<slug>.json    one file per main-site page (SEO meta + cleaned HTML)
  src/content/posts/<slug>.json    one file per blog post (meta + body HTML)
  src/data/redirects.json          301s discovered on the live site (chains flattened)
  src/data/images.json             every HubSpot-hosted file referenced -> local path
  src/data/blog-meta.json          blog/academy listing intros, tags

Usage:
  python3 -I scripts/migrate/extract.py <crawl-dir> <repo-root>

The extractor never alters page wording, titles or meta descriptions: those are
copied byte-for-byte so Google sees the same content after the move.
"""
import json, os, re, sys, hashlib, urllib.parse
from bs4 import BeautifulSoup, Comment, NavigableString

CRAWL, ROOT = sys.argv[1], sys.argv[2]
crawl = json.load(open(os.path.join(CRAWL, 'crawl.json')))

MAIN = 'hipelpools.ca'
BLOG = 'blog.hipelpools.ca'
PORTAL = '21723658'

images = {}  # original url (normalized) -> local path


# ---------------------------------------------------------------- helpers
def local_file(url):
    """Map a HubSpot file URL to a local /files/... path. Returns None for non-HubSpot URLs."""
    if not url:
        return None
    url = url.replace('&amp;', '&').strip()
    if url.startswith('//'):
        url = 'https:' + url
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or '').lower()
    path = urllib.parse.unquote(p.path)
    rel = None
    if host in (MAIN, 'www.' + MAIN, BLOG, '') and path.startswith('/hubfs/'):
        rel = path[len('/hubfs/'):]
    elif host in (MAIN, 'www.' + MAIN, BLOG, '') and path.startswith('/hs-fs/hubfs/'):
        rel = path[len('/hs-fs/hubfs/'):]
    elif host.endswith('hubspotusercontent-na1.net') or host.startswith('f.hubspotusercontent') or host == 'cdn2.hubspot.net':
        m = re.search(r'/hubfs/(?:%s/)?(.*)$' % PORTAL, path)
        if m:
            rel = m.group(1)
    m = re.match(r'^/cta/default/%s/(interactive-\d+\.(?:png|jpe?g|gif))$' % PORTAL, path) if host == 'no-cache.hubspot.com' else None
    if m:
        loc = '/files/cta/' + m.group(1)
        images['https://no-cache.hubspot.com' + path] = loc
        return loc
    if rel is None or rel.startswith('hub_generated/'):
        return None
    # HubSpot video thumbnails live "inside" the video path (video.mp4/medium.jpg)
    orig_rel = rel
    m = re.match(r'(.*)\.(mp4|mov|webm)/(.+)$', rel, re.I)
    if m:
        rel = m.group(1) + '-' + m.group(3)
    # web-safe local name: keep folders, slugify each segment, keep extension
    parts = []
    for seg in rel.split('/'):
        base, dot, ext = seg.rpartition('.')
        if not dot:
            base, ext = seg, ''
        s = re.sub(r'[^a-zA-Z0-9]+', '-', base).strip('-').lower() or 'file'
        parts.append(s + ('.' + ext.lower() if ext else ''))
    loc = '/files/' + '/'.join(parts)
    if loc.endswith('.mov'):
        loc = loc[:-4] + '.mp4'  # transcoded by download_files.py for browser support
    src = 'https://%s/hubfs/%s' % (MAIN, urllib.parse.quote(orig_rel))
    images[src] = loc
    return loc


FILE_PREFIX = ''  # '' on the main site; 'https://hipelpools.ca' while cleaning blog content


def rewrite_link(href, page_host):
    """Relative for same-host links, absolute across hosts; HubSpot files -> /files/..."""
    if not href:
        return href
    href = href.strip()
    if href.startswith('javascript:'):
        return None
    f = local_file(href)
    if f:
        return FILE_PREFIX + f
    p = urllib.parse.urlsplit(href)
    host = (p.hostname or '').lower()
    if host == 'www.' + MAIN:
        host = MAIN
    if not host:
        return href
    if host == page_host:
        path = p.path or '/'
        return path + ('?' + p.query if p.query else '') + ('#' + p.fragment if p.fragment else '')
    if host in (MAIN, BLOG):
        return urllib.parse.urlunsplit(('https', host, p.path or '/', p.query, p.fragment))
    return href


DROP_ATTR = re.compile(r'^(data-hs-.*|data-widget-type|data-x|data-w|data-y|tmp-data-aos.*|data-aos.*|'
                       r'data-pwr-.*|data-hs-cos-.*|data-start|data-end|category|action|label|fetchpriority|decoding)$')


def rename_cls(c):
    return 'hp-' + c[4:] if c.startswith('pwr-') else ('hp--' + c[5:] if c.startswith('pwr--') else c)


DROP_CLS = re.compile(r'^(hs_cos_wrapper.*|widget-type-.*|lazyload|lazyloaded|vanilla|dnd-module|'
                      r'hs-image-widget|pwr-js-.*)$')


def clean_fragment(node, page_host, eager_first=True):
    """Clean one BeautifulSoup subtree in place."""
    # must run before scripts are removed: form embeds are identified by their <script>
    fix_hubspot_widgets(node)
    for t in node.find_all(['script', 'noscript', 'link', 'meta']):
        t.decompose()  # JSON-LD is handled at page level
    for c in node.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for f in node.select('.hbspt-form, [id^="hs_form_target"]'):
        f.decompose()
    seen_img = False
    for el in node.find_all(True):
        # lazy loading attrs -> real attrs
        for a, b in (('data-src', 'src'), ('data-srcset', 'srcset'), ('data-splide-lazy', 'src'), ('data-bg', 'data-bg')):
            if el.has_attr(a) and a != b:
                el[b] = el[a]
                del el[a]
        for a in list(el.attrs):
            if DROP_ATTR.match(a) or not re.match(r'^[a-zA-Z_:][-a-zA-Z0-9_:.]*$', a):
                del el[a]
        if el.has_attr('class'):
            cls = [rename_cls(c) for c in el['class'] if not DROP_CLS.match(c)]
            if cls:
                el['class'] = cls
            else:
                del el['class']
        if el.get('style', None) == '':
            del el['style']
        if el.has_attr('id') and el['id'].startswith('hs_cos_wrapper_'):
            el['id'] = 'm-' + el['id'][len('hs_cos_wrapper_'):]
        if el.has_attr('href'):
            nh = rewrite_link(el['href'], page_host)
            if nh is None:
                el['href'] = '#'
                el['role'] = 'button'
            else:
                el['href'] = nh
        if el.has_attr('data-lightbox-href'):
            el['data-lightbox-href'] = rewrite_link(el['data-lightbox-href'], page_host) or '#'
        if el.name == 'video' and el.get('src'):
            loc = local_file(el['src'])
            if loc:
                el['src'] = FILE_PREFIX + loc
        if el.name in ('img', 'source'):
            src = el.get('src')
            if src:
                loc = local_file(src)
                if loc:
                    el['src'] = FILE_PREFIX + loc
            if el.has_attr('srcset'):
                # HubSpot resizes on the fly (?width=). We serve one optimized file per image.
                first = el['srcset'].split(',')[0].strip().split(' ')[0]
                loc = local_file(first)
                if el.name == 'source':
                    if loc:
                        el['srcset'] = FILE_PREFIX + loc
                else:
                    del el['srcset']
                    if not el.get('src') and loc:
                        el['src'] = FILE_PREFIX + loc
            if el.has_attr('sizes'):
                del el['sizes']
            if el.name == 'img':
                if not seen_img and eager_first:
                    seen_img = True
                    el['loading'] = 'eager'
                elif not el.has_attr('loading'):
                    el['loading'] = 'lazy'
        if el.has_attr('style') and 'url(' in el['style']:
            def rep(m):
                loc = local_file(m.group(2))
                return 'url(%s%s%s)' % (m.group(1), (FILE_PREFIX + loc) if loc else m.group(2), m.group(1))
            el['style'] = re.sub(r'url\(\s*([\'"]?)([^\'")]+)\1\s*\)', rep, el['style'])
        for a in ('data-bg', 'poster'):
            if el.has_attr(a):
                loc = local_file(el[a])
                if loc:
                    el[a] = FILE_PREFIX + loc
    # empty search forms / HubSpot-only widgets
    for f in node.select('form[action="/hs-search-results"]'):
        f.decompose()
    return node


CTA_DEST = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cta-destinations.json')))
QUOTE = 'https://hipelpools.ca/en-ca/request-a-quote'
# HubSpot pop-up CTAs (no URL of their own) -> where each one should go now
POPUP_DEST = {
    '185355309424': 'https://hipelpools.outgrow.us/vinyl-liner-replacement-cost-calculator',
}
# HubSpot-hosted videos (hs-video-widget) -> the original mp4 in the file manager
HS_VIDEOS = {
    '185639880571': 'https://hipelpools.ca/hubfs/Pool%20Opening%20Service%20Highlight-%20Hipel%20Pools.mp4',
    '163282673990': 'https://hipelpools.ca/hubfs/Pool%20Safety%20Cover%20Video.mp4',
}
# Links the theme vendor left pointing at their demo site (broken on the live site today)
DEMO_LINKS = {
    'power-theme-blog-3-col': 'https://blog.hipelpools.ca',
    'power-theme-case-study': 'https://blog.hipelpools.ca',
    'power-theme-about-me': 'https://hipelpools.ca/company/about-us',
}
DEMO_BY_TITLE = {
    'fiberglass pools': 'https://hipelpools.ca/fiberglass-pools/locations/ontario',
    'water features': 'https://hipelpools.ca/pool-accessories/pool-water-features-ontario',
}
fixups = {'cta': 0, 'popup': 0, 'video': 0, 'demo': 0, 'form': 0}
FORM_TYPES = {
    'dc4bd5cd-8934-4e56-9f4f-3e61c22eba1a': 'quote',
    '44a4014d-eeda-4803-ace0-3db4e2261ec7': 'quote',
    '3a7b1bd7-d34e-469b-b1c7-10564e5ef217': 'contact',
    # blog comment forms (6510590d..., fa3900b4...) are intentionally dropped
}


def fix_hubspot_widgets(node):
    """Replace HubSpot-only widgets (CTAs, pop-ups, video player, theme demo links) with plain HTML."""
    for a in node.select('a[href*="/hs/cta/"]'):
        m = re.search(r'webInteractiveContentId=(\d+)', a['href'].replace('&amp;', '&'))
        dest = CTA_DEST.get(m.group(1)) if m else None
        a['href'] = re.sub(r'[?&]hsCtaAttrib=\d+$', '', dest) if dest else QUOTE
        del a['crossorigin']
        fixups['cta'] += 1
    for wrap in node.select('.hs-cta-embed'):
        cid = wrap.get('data-hubspot-wrapper-cta-id')
        a = wrap.find('a')
        if a is not None and (a.get('href') in (None, '#', 'javascript:;') or a['href'].startswith('javascript')):
            a['href'] = POPUP_DEST.get(cid, QUOTE)
            if a.get('role') == 'button':
                del a['role']
            fixups['popup'] += 1
        img = wrap.find('img')
        if img is not None and img.has_attr('onerror'):
            del img['onerror']
    for a in node.select('a[class*="hs-cta-trigger-button"]'):
        cid = next((c.rsplit('-', 1)[-1] for c in a.get('class', []) if re.match(r'hs-cta-trigger-button-\d+', c)), None)
        a['href'] = POPUP_DEST.get(cid, QUOTE)
        a['class'] = [c for c in a['class'] if not c.startswith('hs-cta-trigger')]
        if a.get('role') == 'button':
            del a['role']
        if a.get('target') == '_blank':
            del a['target']
        fixups['popup'] += 1
    # HubSpot forms (rendered by HubSpot JS) -> placeholder our own form component fills in
    for sc in node.find_all('script'):
        txt = sc.string or ''
        m = re.search(r"formId['\"]?\s*:\s*['\"]([0-9a-f-]{36})", txt)
        if m and m.group(1) in FORM_TYPES:
            sc.replace_with(BeautifulSoup('<div data-hp-form="%s"></div>' % FORM_TYPES[m.group(1)], 'html.parser'))
            fixups['form'] += 1
    for t in node.select('[id^="hs_form_target"]'):
        m = re.search(r'([0-9a-f]{8}-[0-9a-f-]{27})', t['id'] + ' ' + t.get('data-form-id', ''))
        kind = FORM_TYPES.get(m.group(1)) if m else None
        if kind:
            t.replace_with(BeautifulSoup('<div data-hp-form="%s"></div>' % kind, 'html.parser'))
            fixups['form'] += 1
    for fr in node.select('.hs-form-frame[data-form-id]'):
        fr.replace_with(BeautifulSoup('<div data-hp-form="%s"></div>' % FORM_TYPES.get(fr['data-form-id'], 'quote'), 'html.parser'))
        fixups['form'] += 1
    for w in node.select('.hs-video-widget'):
        fr = w.find('iframe')
        vid = fr.get('data-hsv-id') if fr is not None else None
        src = HS_VIDEOS.get(vid)
        if src:
            loc = local_file(src)
            poster = loc[:-4] + '-poster.jpg'
            w.replace_with(BeautifulSoup(
                '<div class="hp-video"><video controls preload="none" playsinline poster="%s%s" src="%s%s"></video></div>'
                % (FILE_PREFIX, poster, FILE_PREFIX, loc), 'html.parser'))
            fixups['video'] += 1
        else:
            print('  ! unknown HubSpot video', vid, file=sys.stderr)
    for a in node.select('a[href*="hs-sites.com"]'):
        key = a['href'].rstrip('/').rsplit('/', 1)[-1]
        dest = DEMO_LINKS.get(key)
        if not dest:
            box = a.find_parent(class_=re.compile(r'pwr-image-box'))
            t = box.select_one('.pwr-image-box__title') if box is not None else None
            dest = DEMO_BY_TITLE.get(t.get_text(strip=True).lower() if t else '', QUOTE)
        a['href'] = dest
        fixups['demo'] += 1


def css_rewrite(css):
    css = re.sub(r'#hs_cos_wrapper_', '#m-', css)
    css = re.sub(r'\.pwr--', '.hp--', css)
    css = re.sub(r'\.pwr-', '.hp-', css)

    def rep(m):
        loc = local_file(m.group(2))
        return 'url(%s%s%s)' % (m.group(1), loc or m.group(2), m.group(1))
    css = re.sub(r'url\(\s*([\'"]?)([^\'")]+)\1\s*\)', rep, css)
    return css


def page_css(soup):
    """Per-page CSS HubSpot generates from editor settings (row colours, module colours, padding)."""
    out = []
    for st in soup.find_all('style'):
        t = st.string or st.get_text() or ''
        if '@font-face' in t or 'cta_button{' in t or 'hs-search-field' in t or t.strip().startswith('body { margin:0px'):
            continue
        if not re.search(r'#hs_cos_wrapper_|dnd_area|dnd_|\.row-number|widget_|module_|cell_|DnD', t):
            continue
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            out.append(css_rewrite(t))
    return '\n'.join(out)


def head_meta(soup):
    def m(sel, attr='content'):
        t = soup.select_one(sel)
        return t.get(attr) if t else None
    meta = {
        'title': soup.title.get_text() if soup.title else '',
        'description': m('meta[name="description"]'),
        'canonical': m('link[rel="canonical"]', 'href'),
        'robots': m('meta[name="robots"]'),
        'ogTitle': m('meta[property="og:title"]'),
        'ogDescription': m('meta[property="og:description"]'),
        'ogImage': m('meta[property="og:image"]'),
        'ogType': m('meta[property="og:type"]'),
        'twitterCard': m('meta[name="twitter:card"]'),
        'lang': (soup.html.get('lang') if soup.html else None) or 'en',
        'prev': m('link[rel="prev"]', 'href'),
        'next': m('link[rel="next"]', 'href'),
    }
    if meta['ogImage']:
        meta['ogImage'] = local_file(meta['ogImage']) or meta['ogImage']
    ld = []
    for s in soup.find_all('script', type='application/ld+json'):
        raw = (s.string or '').strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            try:
                data = json.loads(re.sub(r',\s*([}\]])', r'\1', raw))
            except Exception:
                print('  ! unparsable JSON-LD skipped', file=sys.stderr)
                continue
        ld.append(data)
    meta['jsonld'] = ld
    return meta


def fix_ld_urls(obj):
    if isinstance(obj, dict):
        return {k: fix_ld_urls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fix_ld_urls(v) for v in obj]
    if isinstance(obj, str) and ('hubfs' in obj):
        loc = local_file(obj)
        return ('https://hipelpools.ca' + loc) if loc else obj
    return obj


def slug_for(url):
    p = urllib.parse.urlsplit(url)
    path = p.path
    s = path.strip('/') or 'index'
    return re.sub(r'[^a-zA-Z0-9.-]+', '__', s) if path != '/' else 'index'


# ---------------------------------------------------------------- run
os.makedirs(os.path.join(ROOT, 'src/content/pages'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'src/content/posts'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'src/data'), exist_ok=True)

pages, posts, listings = [], [], {}
baseline = {}
# site-chrome files (logos in header/footer, favicon) referenced by our own templates
for u in ['https://hipelpools.ca/hubfs/favicon-1.png',
          'https://hipelpools.ca/hubfs/Imported%20sitepage%20images/Hipel-Logo-Clear-white-1.svg',
          'https://hipelpools.ca/hubfs/Hipel%20Logo%20Clear%20-%20500%20x%20214%20-%20Clear%20Background.png']:
    local_file(u)

for url, info in sorted(crawl.items()):
    if info['status'] != 200:
        continue
    html = open(info['file']).read()
    soup = BeautifulSoup(html, 'lxml')
    host = urllib.parse.urlsplit(url).hostname
    path = urllib.parse.urlsplit(url).path or '/'
    meta = head_meta(soup)
    # SEO baseline of the live HubSpot page (used by scripts/check-seo.mjs after every build)
    _main = soup.select_one('main') or soup.body
    _txt = BeautifulSoup(str(_main), 'lxml')
    for _t in _txt.select('script, style, noscript, .pwr-post-social, form'):
        _t.decompose()
    baseline[url] = {
        'title': meta['title'], 'description': meta['description'], 'canonical': meta['canonical'],
        'robots': meta['robots'],
        'h1': [h.get_text(' ', strip=True) for h in _main.find_all('h1')],
        'words': len(_txt.get_text(' ', strip=True).split()),
        'jsonld': len(meta['jsonld']),
    }
    meta['jsonld'] = fix_ld_urls(meta['jsonld'])
    is_post = host == BLOG and soup.select_one('.pwr-post-body') is not None
    is_listing = host == BLOG and not is_post

    if is_post:
        body = soup.select_one('.pwr-post-body')
        for junk in body.select('progress, .pwr-post-social, .addthis_inline_share_toolbox'):
            junk.decompose()
        FILE_PREFIX = 'https://' + MAIN
        clean_fragment(body, host, eager_first=False)
        FILE_PREFIX = ''
        hdr = soup.select_one('.pwr-post-header')
        title_el = soup.select_one('.pwr-post-header h1') or soup.select_one('h1')
        feat = soup.select_one('.pwr-post-header img, .pwr-post-header__img img, .pwr-post-header picture img')
        feat_src = None
        if feat is not None:
            feat_src = feat.get('data-src') or feat.get('src')
        if not feat_src and hdr is not None:
            m = re.search(r'url\([\'"]?([^\'")]+)', str(hdr))
            feat_src = m.group(1) if m else None
        bp = [d for d in meta['jsonld'] if isinstance(d, dict) and d.get('@type') == 'BlogPosting' and d.get('datePublished')]
        tags = []
        for a in soup.select('a[href*="/tag/"]'):
            if '.pwr-post-header' in str(a.parent) or True:
                href = a.get('href', '')
                if re.search(r'/tag/[^/]+$', href) and a.get_text(strip=True):
                    t = (urllib.parse.urlsplit(href).path.rsplit('/', 1)[-1], a.get_text(strip=True))
                    if t not in tags:
                        tags.append(t)
        blog = 'academy' if path.startswith('/academy/') else 'main'
        # tags for a post are the ones linked inside the post header/topics area only
        post_tags = []
        for a in soup.select('.pwr-post-header a[href*="/tag/"], .pwr-post-tags a[href*="/tag/"], .pwr-post-topics a[href*="/tag/"]'):
            t = urllib.parse.urlsplit(a['href']).path.rsplit('/', 1)[-1]
            if t not in [x['slug'] for x in post_tags]:
                post_tags.append({'slug': t, 'name': a.get_text(strip=True)})
        author = soup.select_one('a[href*="/author/"]')
        posts.append({
            'url': url, 'path': path, 'blog': blog, 'slug': slug_for(url),
            'meta': meta,
            'heading': title_el.get_text(' ', strip=True) if title_el else meta['title'],
            'datePublished': bp[0]['datePublished'] if bp else None,
            'dateModified': bp[0].get('dateModified') if bp else None,
            'author': {'name': (bp[0]['author']['name'] if bp else 'Kadison Hipel'),
                       'slug': 'kadison-hipel'},
            'featuredImage': local_file(feat_src) if feat_src else None,
            'featuredAlt': feat.get('alt') if feat is not None else None,
            'tags': post_tags,
            'html': body.decode_contents().strip(),
        })
    elif is_listing:
        intro = soup.select_one('.pwr-hero, .pwr-blog-listing__intro, .pwr-sec-txt')
        listings[path] = {'url': url, 'meta': meta}
    else:
        main = soup.select_one('main') or soup.body
        clean_fragment(main, host)
        pages.append({
            'url': url, 'path': path, 'slug': slug_for(url),
            'meta': meta,
            'css': page_css(soup),
            'html': main.decode_contents().strip(),
        })

# ---------------------------------------------------------------- blog structure
post_by_path = {p['path']: p for p in posts}
blogs = {}
for path, lst in listings.items():
    blog = 'academy' if path.startswith('/academy') else 'main'
    b = blogs.setdefault(blog, {'tags': {}, 'title': None, 'description': None, 'hero': None, 'heading': None})
    soup = BeautifulSoup(open(crawl[lst['url']]['file']).read(), 'lxml')
    main = soup.select_one('main')
    if path in ('/', '/academy'):
        b['title'] = lst['meta']['title']
        b['description'] = lst['meta']['description']
        h1 = main.select_one('h1')
        b['heading'] = h1.get_text(' ', strip=True) if h1 else None
        img = main.select_one('.pwr-hero img')
        b['hero'] = local_file(img.get('src')) if img is not None else None
        ov = main.select_one('.pwr-hero .pwr-bg-overlay')
        b['heroOverlay'] = ov.get('style') if ov is not None else None
        for a in main.select('.pwr-filter__link'):
            m = re.search(r'/tag/([^/?#]+)$', a.get('href', ''))
            if m:
                b['tags'][m.group(1)] = a.get_text(strip=True)
    for a in main.select('a.pwr-post-item[href]'):
        pp = urllib.parse.urlsplit(a['href']).path
        if pp in post_by_path and not post_by_path[pp].get('listImage'):
            im = a.select_one('.pwr-post-item__img')
            mm = re.search(r'url\(([^)]+)\)', im.get('style', '')) if im is not None else None
            post_by_path[pp]['listImage'] = local_file(mm.group(1)) if mm else None
            ex = a.select_one('.pwr-post-item__desc, .pwr-post-item__summary, p')
            post_by_path[pp]['excerpt'] = ex.get_text(' ', strip=True) if ex is not None else None
    m = re.search(r'/tag/([^/]+?)(?:/page/\d+)?$', path)
    if m:
        for a in main.select('a.pwr-post-item[href]'):
            pp = urllib.parse.urlsplit(a['href']).path
            if pp in post_by_path:
                tg = post_by_path[pp]['tags']
                if m.group(1) not in [t['slug'] for t in tg]:
                    tg.append({'slug': m.group(1), 'name': None})
    if '/author/' in path and '/page/' not in path:
        b.setdefault('authors', {})[path.rsplit('/', 1)[-1]] = {
            'title': lst['meta']['title'], 'description': lst['meta']['description'],
            'name': (main.select_one('h1').get_text(strip=True) if main.select_one('h1') else '')}
for p in posts:
    names = blogs.get(p['blog'], {}).get('tags', {})
    for t in p['tags']:
        t['name'] = t['name'] or names.get(t['slug'], t['slug'])
json.dump(blogs, open(os.path.join(ROOT, 'src/data/blogs.json'), 'w'), indent=1, ensure_ascii=False)

for p in posts:
    json.dump(p, open(os.path.join(ROOT, 'src/content/posts', p['slug'] + '.json'), 'w'), indent=1, ensure_ascii=False)
for p in pages:
    json.dump(p, open(os.path.join(ROOT, 'src/content/pages', p['slug'] + '.json'), 'w'), indent=1, ensure_ascii=False)
json.dump(listings, open(os.path.join(ROOT, 'src/data/blog-listings.json'), 'w'), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- redirects (flatten chains)
r301 = {u: v['location'] for u, v in crawl.items() if v['status'] in (301, 302, 307, 308) and v.get('location')}


def final(u, depth=0):
    while u in r301 and depth < 20:
        u = urllib.parse.urljoin(u, r301[u]); depth += 1
    return u


redirects = []
for src in sorted(r301):
    dst = final(src)
    st = crawl.get(dst, {}).get('status')
    redirects.append({'from': src, 'to': dst, 'finalStatus': st})
json.dump(redirects, open(os.path.join(ROOT, 'src/data/redirects.json'), 'w'), indent=1)
json.dump({'pages': baseline, 'redirects': {r['from']: r['to'] for r in redirects},
           'gone': sorted(u for u, v in crawl.items() if v['status'] == 404)},
          open(os.path.join(ROOT, 'src/data/seo-baseline.json'), 'w'), indent=1, ensure_ascii=False)
json.dump(dict(sorted(images.items())), open(os.path.join(ROOT, 'src/data/images.json'), 'w'), indent=1)
print('fixups', fixups)
print('pages', len(pages), 'posts', len(posts), 'listings', len(listings), 'redirects', len(redirects), 'files', len(images))
