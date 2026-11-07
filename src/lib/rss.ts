import { SITE, type Post } from './content';

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export function rssFeed(title: string, link: string, items: Post[]) {
  const body = items
    .map((p) => {
      const url = SITE.blogHost + p.path;
      return `<item><title>${esc(p.heading)}</title><link>${url}</link><guid>${url}</guid>` +
        `<pubDate>${new Date(p.datePublished).toUTCString()}</pubDate>` +
        `<description>${esc(p.meta.description || p.excerpt || '')}</description>` +
        `<dc:creator>${esc(p.author.name)}</dc:creator></item>`;
    })
    .join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>` +
    `<title>${esc(title)}</title><link>${link}</link><description>${esc(title)}</description><language>en</language>${body}</channel></rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
}
