// SEO parity check: compares the built sites (dist/main, dist/blog) with the snapshot of the
// live HubSpot site in src/data/seo-baseline.json. Run after `npm run build`:
//   npm run check:seo
// Fails (exit 1) if any old URL would 404, or if a title / description / canonical / H1 changed.
import fs from 'node:fs';
import path from 'node:path';

const baseline = JSON.parse(fs.readFileSync('src/data/seo-baseline.json', 'utf8'));
const dist = { 'hipelpools.ca': path.resolve('dist/main'), 'blog.hipelpools.ca': path.resolve('dist/blog') };

const redirectTables = {};
for (const [host, dir] of Object.entries(dist)) {
  const map = new Map();
  const f = path.join(dir, '_redirects');
  if (fs.existsSync(f)) for (const l of fs.readFileSync(f, 'utf8').split('\n')) {
    const [from, to] = l.trim().split(/\s+/);
    if (from && to && !from.startsWith('#')) map.set(from, to);
  }
  redirectTables[host] = map;
}

/** Resolve a URL the way Cloudflare Pages will: redirects first, then the static file. */
function resolve(url, hops = 0) {
  const u = new URL(url);
  const dir = dist[u.hostname];
  if (!dir || hops > 5) return { status: 0 };
  const p = decodeURIComponent(u.pathname);
  const r = redirectTables[u.hostname].get(u.pathname);
  if (r) return { status: 301, to: new URL(r, url).href, final: resolve(new URL(r, url).href, hops + 1) };
  const cands = p.endsWith('/')
    ? [path.join(dir, p, 'index.html'), p === '/' ? path.join(dir, 'index.html') : path.join(dir, p.slice(0, -1) + '.html')]
    : [path.join(dir, p + '.html'), path.join(dir, p, 'index.html'), path.join(dir, p)];
  for (const c of cands) if (fs.existsSync(c) && fs.statSync(c).isFile()) return { status: 200, file: c };
  return { status: 404 };
}

const decode = (s) => s?.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#x27;/g, "'").replace(/&nbsp;|&#160;/g, ' ');
const get = (html, re) => decode(html.match(re)?.[1]);
const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();

let errors = 0, warnings = 0;
const err = (m) => { errors++; console.log('  ✗ ' + m); };
const warn = (m) => { warnings++; console.log('  ! ' + m); };

console.log(`Checking ${Object.keys(baseline.pages).length} pages and ${Object.keys(baseline.redirects).length} redirects…\n`);
for (const [url, old] of Object.entries(baseline.pages)) {
  const r = resolve(url);
  const final = r.status === 301 ? r.final : r;
  if (final.status !== 200) { console.log(url); err(`not found in new build (status ${final.status})`); continue; }
  if (r.status === 301) { console.log(url); warn(`was a page, now redirects to ${r.to}`); continue; }
  const html = fs.readFileSync(final.file, 'utf8');
  const problems = [];
  const title = get(html, /<title>([^<]*)<\/title>/);
  if (norm(title) !== norm(old.title)) problems.push(['err', `title changed: "${old.title}" → "${title}"`]);
  const desc = get(html, /<meta name="description" content="([^"]*)"/);
  if (old.description && norm(desc) !== norm(old.description)) problems.push(['err', `description changed`]);
  const canon = get(html, /<link rel="canonical" href="([^"]*)"/);
  if (old.canonical && canon !== old.canonical) problems.push(['err', `canonical changed: ${old.canonical} → ${canon}`]);
  if (!old.canonical && canon !== url && !(url.endsWith('/page/1'))) problems.push(['warn', `canonical added: ${canon}`]);
  const robots = get(html, /<meta name="robots" content="([^"]*)"/);
  if (norm(robots) !== norm(old.robots)) problems.push(['err', `robots changed: ${old.robots} → ${robots}`]);
  const h1 = [...html.matchAll(/<h1[^>]*>([\s\S]*?)<\/h1>/g)].map((m) => norm(decode(m[1].replace(/<[^>]+>/g, ' '))));
  for (const h of old.h1) if (!h1.includes(norm(h))) problems.push(['err', `H1 missing: "${h}"`]);
  const body = html.match(/<main[^>]*>([\s\S]*)<\/main>/)?.[1] || '';
  const words = decode(body.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<form[\s\S]*?<\/form>/g, ' ').replace(/<[^>]+>/g, ' ')).split(/\s+/).filter(Boolean).length;
  if (words < old.words * 0.85) problems.push(['warn', `less text than before: ${words} words vs ${old.words}`]);
  const ld = (html.match(/application\/ld\+json/g) || []).length;
  if (ld < old.jsonld) problems.push(['err', `structured data blocks: ${ld} (was ${old.jsonld})`]);
  if (problems.length) {
    console.log(url);
    for (const [k, m] of problems) (k === 'err' ? err : warn)(m);
  }
}
for (const [from, to] of Object.entries(baseline.redirects)) {
  const r = resolve(from);
  if (r.status !== 301 || r.to.replace(/\/$/, '') !== to.replace(/\/$/, '')) {
    console.log(from);
    err(`redirect lost: expected 301 → ${to}, got ${r.status}${r.to ? ' → ' + r.to : ''}`);
  } else if (r.final.status !== 200) { console.log(from); err(`redirect target is ${r.final.status}: ${to}`); }
}
// every internal link in the new build should resolve
const linkFails = new Map();
for (const [host, dir] of Object.entries(dist)) {
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
  for (const f of walk(dir).filter((x) => x.endsWith('.html'))) {
    const html = fs.readFileSync(f, 'utf8');
    for (const m of html.matchAll(/(?:href|src)="([^"#?]+)/g)) {
      let link = m[1];
      if (link.startsWith('/') && !link.startsWith('//')) link = `https://${host}${link}`;
      if (!/^https:\/\/(blog\.)?hipelpools\.ca\//.test(link + '/') || link.includes('/api/')) continue;
      if (link.includes('/_astro/') || link.endsWith('.xml')) continue;
      const r = resolve(link);
      const st = r.status === 301 ? r.final.status : r.status;
      if (st !== 200 && !(new URL(link).hostname === 'hipelpools.ca' && link.includes('/files/') && dist['hipelpools.ca'] && fs.existsSync(path.join(dist['hipelpools.ca'], decodeURIComponent(new URL(link).pathname))))) {
        if (!linkFails.has(link)) linkFails.set(link, path.relative(dir, f));
      }
    }
  }
}
for (const [l, f] of linkFails) { console.log(`broken link ${l} (in ${f})`); warn('internal link does not resolve'); }

console.log(`\n${errors} error(s), ${warnings} warning(s)`);
process.exit(errors ? 1 : 0);
