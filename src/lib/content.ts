// Content access for both builds (main site + blog subdomain).
// Pages and posts live as JSON in src/content (generated once from HubSpot by scripts/migrate,
// then edited by hand going forward).
import site from '../data/site.json';
import blogsData from '../data/blogs.json';

export type Meta = {
  title: string;
  description?: string | null;
  canonical?: string | null;
  robots?: string | null;
  ogTitle?: string | null;
  ogDescription?: string | null;
  ogImage?: string | null;
  ogType?: string | null;
  twitterCard?: string | null;
  lang?: string;
  jsonld?: unknown[];
};

export type Page = { url: string; path: string; slug: string; meta: Meta; css: string; html: string };

export type Post = {
  url: string;
  path: string;
  blog: 'main' | 'academy';
  slug: string;
  meta: Meta;
  heading: string;
  datePublished: string;
  dateModified?: string | null;
  author: { name: string; slug: string };
  featuredImage?: string | null;
  featuredAlt?: string | null;
  listImage?: string | null;
  excerpt?: string | null;
  tags: { slug: string; name: string }[];
  html: string;
};

export const TARGET: 'main' | 'blog' = (process.env.SITE_TARGET as 'main' | 'blog') || 'main';
export const SITE = site;
export const HOST = TARGET === 'blog' ? site.blogHost : site.mainHost;
export const blogs = blogsData as Record<string, any>;

const pageModules = import.meta.glob<Page>('../content/pages/*.json', { eager: true, import: 'default' });
const postModules = import.meta.glob<Post>('../content/posts/*.json', { eager: true, import: 'default' });

export const pages: Page[] = Object.values(pageModules).sort((a, b) => a.path.localeCompare(b.path));
export const posts: Post[] = Object.values(postModules).sort(
  (a, b) => +new Date(b.datePublished) - +new Date(a.datePublished)
);

export const POSTS_PER_PAGE = 10;

/** Blog root path for each blog on the blog host. */
export const blogRoot = (blog: string) => (blog === 'academy' ? '/academy' : '');

/**
 * Preview mode: before the real domains are switched over, the two sites run on Cloudflare
 * preview addresses (e.g. https://hipelpools.pages.dev). Set SITE_MAIN_URL / SITE_BLOG_URL
 * at build time and every link and image between the two sites points at the preview copies.
 * Canonical tags, structured data, sitemaps and RSS always keep the real hipelpools.ca addresses.
 */
export const LIVE = {
  main: (process.env.SITE_MAIN_URL || site.mainHost).replace(/\/$/, ''),
  blog: (process.env.SITE_BLOG_URL || site.blogHost).replace(/\/$/, ''),
};
export const PREVIEW = LIVE.main !== site.mainHost || LIVE.blog !== site.blogHost;

/** Point absolute hipelpools.ca / blog.hipelpools.ca URLs in content at the preview sites. */
export function localize(html: string) {
  if (!PREVIEW) return html;
  return html
    .replace(/https:\/\/blog\.hipelpools\.ca(?=[/"'?#\s)]|$)/g, LIVE.blog)
    .replace(/https:\/\/(?:www\.)?hipelpools\.ca(?=[/"'?#\s)]|$)/g, LIVE.main);
}

/** Absolute URL helper for links that cross between the two hosts. */
export function href(path: string, host: 'main' | 'blog') {
  if (/^https?:/.test(path)) return localize(path);
  if ((host === 'blog') === (TARGET === 'blog')) return path;
  return (host === 'blog' ? LIVE.blog : LIVE.main) + path;
}

export function readingMinutes(html: string) {
  const words = html.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 250));
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'America/Toronto' });
}

export function chunk<T>(arr: T[], n: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n));
  return out.length ? out : [[]];
}
