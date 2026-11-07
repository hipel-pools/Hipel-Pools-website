// @ts-check
import { defineConfig } from 'astro/config';

// Two deployments are built from this one project (see package.json scripts):
//   SITE_TARGET=main -> https://hipelpools.ca        (dist/main)
//   SITE_TARGET=blog -> https://blog.hipelpools.ca   (dist/blog)
const target = process.env.SITE_TARGET || 'main';

export default defineConfig({
  site: target === 'blog' ? 'https://blog.hipelpools.ca' : 'https://hipelpools.ca',
  // HubSpot served pages without a trailing slash (/company/about-us). Build "about-us.html"
  // files so Cloudflare Pages serves the same URLs; scripts/postbuild.mjs handles the one
  // page whose URL ends in "/" (/pool-service/pool-closing/).
  build: { format: 'file', inlineStylesheets: 'auto' },
  trailingSlash: 'ignore',
  compressHTML: true,
});
