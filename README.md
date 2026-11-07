# Hipel Pools website

The hipelpools.ca and blog.hipelpools.ca websites, moved off HubSpot to a fast static site
built with [Astro](https://astro.build). It is designed to be hosted for free on
**Cloudflare Pages**.

The content, URLs, page titles, meta descriptions, canonical tags and structured data were
copied from the live HubSpot site, so Google sees the same pages at the same addresses.
See [MIGRATION.md](MIGRATION.md) for the launch checklist.

## What's where

| Path | What it is |
| --- | --- |
| `src/content/pages/*.json` | One file per hipelpools.ca page: SEO fields (`meta`) and the page content (`html`) |
| `src/content/posts/*.json` | One file per blog post (both the main blog and the Academy) |
| `src/data/site.json` | Phone, email, address, logo, **main menu**, footer links, Google Analytics IDs |
| `src/data/blogs.json` | Blog names, descriptions and tag/category names |
| `src/styles/` | All the styling (`global.css` = header/footer/blog, `sections.css` = page sections) |
| `src/components/` | Header, footer, forms, blog layouts |
| `public/files/` | All images, PDFs and videos (copied from HubSpot's file manager) |
| `functions/api/form.ts` | Handles quote and contact form submissions (emails them to you) |
| `scripts/` | Build helpers, the local preview server, and the SEO check |
| `scripts/migrate/` | One-time HubSpot export scripts. Kept for reference; you don't need to run them again |

## Working on the site

You need [Node.js 22+](https://nodejs.org).

```bash
npm install
npm run dev            # live preview of hipelpools.ca at http://localhost:4321
SITE_TARGET=blog npm run dev   # live preview of the blog
npm run build          # builds both sites into dist/main and dist/blog
npm run check:seo      # confirms no URL, title, description or canonical was lost
node scripts/serve.mjs dist/main 4321   # preview a finished build (same URL rules as Cloudflare)
```

### Common edits

* **Change text on a page.** Open its file in `src/content/pages/` (the file name is the URL,
  with `/` written as `__`). Edit the text inside `"html"`. Don't change `"meta"` unless you
  mean to change what Google shows.
* **Change a page title or meta description.** Edit `meta.title` / `meta.description` in the
  same file.
* **Add a blog post.** Copy an existing file in `src/content/posts/`, give it a new
  `path`/`slug`, and update `heading`, `datePublished`, `meta` and `html`. It appears on the blog
  home page, its tag pages, the RSS feed and the sitemap automatically.
* **Change the menu, phone number or email.** Edit `src/data/site.json`.
* **Add an image.** Put it in `public/files/` and reference it as `/files/your-image.jpg`.

If you change a page's URL, add a redirect from the old URL. Add it to
`src/data/redirects.json` (or straight into `scripts/postbuild.mjs`).

## Hosting on Cloudflare Pages (free)

The main site and the blog are two Cloudflare Pages projects built from this one repository.

| Setting | Main site | Blog |
| --- | --- | --- |
| Project name | `hipelpools` | `hipelpools-blog` |
| Build command | `npm run build:main` | `npm run build:blog` |
| Build output directory | `dist/main` | `dist/blog` |
| Custom domains | `hipelpools.ca`, `www.hipelpools.ca` | `blog.hipelpools.ca` |
| Environment variables | `NODE_VERSION=22`, `RESEND_API_KEY`, `FORM_TO`, `FORM_FROM` | `NODE_VERSION=22` |

The blog uses the images hosted on the main site, so deploy the main site first.

### Preview mode (before switching domains)

Add these two environment variables to **both** projects while you review the site on the
free `*.pages.dev` addresses:

| Variable | Value (use your projects' real addresses) |
| --- | --- |
| `SITE_MAIN_URL` | `https://hipelpools.pages.dev` |
| `SITE_BLOG_URL` | `https://hipelpools-blog.pages.dev` |

While they are set, links and images between the two sites point at the preview copies.
Every page is marked `noindex` and `robots.txt` blocks crawlers, so Google never sees the
preview, and Google Analytics/Tag Manager are switched off so test visits don't count.
Canonical tags still name the real hipelpools.ca addresses.

**On launch day, delete both variables and redeploy both projects.** Even after launch,
`*.pages.dev` addresses always send a `noindex` header.

### Forms

The quote form and the contact form have the same fields as the HubSpot versions. They post
to `/api/form`, which emails the submission (with any uploaded file attached) to you through
[Resend](https://resend.com). Resend's free plan allows 3,000 emails a month.

1. Create a Resend account and verify the `hipelpools.ca` domain (Resend shows you the DNS records to add).
2. Create an API key, and add it as `RESEND_API_KEY` (encrypted) on the **main** Pages project.
3. Optional: set `FORM_TO` (default `sales@hipelpools.ca`; separate multiple addresses with commas)
   and `FORM_FROM` (default `Hipel Pools Website <website@hipelpools.ca>`).

After a successful quote request the visitor lands on `/thankyou-for-requesting-a-quote`, as before.
GTM receives a `form_submission` event, so conversion tracking can stay in place.
