// Local preview server that resolves URLs the way Cloudflare Pages does:
//   /a/b      -> a/b.html (or a/b/index.html)
//   /a/b/     -> a/b/index.html (or 308 to /a/b when only a/b.html exists)
//   _redirects rules (exact paths) are honoured with their status codes.
// Usage: node scripts/serve.mjs dist/main 4321
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(process.argv[2] || 'dist/main');
const port = Number(process.argv[3] || 4321);
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.gif': 'image/gif',
  '.pdf': 'application/pdf', '.mp4': 'video/mp4', '.woff2': 'font/woff2', '.woff': 'font/woff', '.xml': 'application/xml', '.txt': 'text/plain', '.ico': 'image/x-icon' };

const redirects = new Map();
const rf = path.join(root, '_redirects');
if (fs.existsSync(rf)) {
  for (const line of fs.readFileSync(rf, 'utf8').split('\n')) {
    const [from, to, code] = line.trim().split(/\s+/);
    if (from && to && !from.startsWith('#')) redirects.set(from, [to, Number(code) || 301]);
  }
}
const isFile = (p) => fs.existsSync(p) && fs.statSync(p).isFile();

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  let p = decodeURIComponent(url.pathname);
  const r = redirects.get(url.pathname) || redirects.get(p);
  if (r) { res.writeHead(r[1], { Location: r[0] }); return res.end(); }
  let file = path.join(root, p);
  if (!file.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (p.endsWith('/')) {
    if (isFile(path.join(file, 'index.html'))) file = path.join(file, 'index.html');
    else if (p !== '/' && isFile(file.slice(0, -1) + '.html')) { res.writeHead(308, { Location: p.slice(0, -1) }); return res.end(); }
  } else if (!isFile(file)) {
    if (isFile(file + '.html')) file += '.html';
    else if (isFile(path.join(file, 'index.html'))) { res.writeHead(308, { Location: p + '/' }); return res.end(); }
  }
  if (!isFile(file)) {
    res.writeHead(404, { 'Content-Type': types['.html'] });
    return res.end(isFile(path.join(root, '404.html')) ? fs.readFileSync(path.join(root, '404.html')) : 'Not found');
  }
  res.writeHead(200, { 'Content-Type': types[path.extname(file).toLowerCase()] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}).listen(port, () => console.log(`Serving ${root} at http://localhost:${port}`));
