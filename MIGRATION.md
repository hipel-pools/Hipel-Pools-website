# HubSpot → Cloudflare Pages migration: launch checklist

## What was migrated

| | Count | Notes |
| --- | --- | --- |
| Main-site pages (hipelpools.ca) | 77 | Includes 3 live pages that were missing from HubSpot's sitemap: Latham fiberglass, weekly maintenance, above-ground pools |
| Blog posts (blog.hipelpools.ca) | 35 | 30 main blog + 5 Academy, plus all tag, author and pagination pages, and both RSS feeds |
| Images, PDFs, videos | 803 | Now hosted at `/files/…`. Oversized photos were resized, and the 90 MB brochure and two videos were compressed |
| Redirects | 20 from HubSpot + ~1,590 file redirects | Old `/hubfs/…` and `/hs-fs/hubfs/…` image and PDF URLs redirect to the new copies |

Every page keeps **exactly** the same URL, `<title>`, meta description, canonical tag, H1, robots
tag and JSON-LD structured data as the live site. `npm run check:seo` verifies this against a
snapshot of the live site (`src/data/seo-baseline.json`). The last run had 0 errors.

Google Analytics (`G-TJ9R3ESTEW`) and Google Tag Manager (`GTM-TT8V4T9C`) use the same IDs,
so your reporting continues without a gap.

## Things that changed (on purpose)

* **HubSpot forms** are replaced by forms with the same fields that email you (see README → Forms).
  Blog comment forms were dropped because they only work on HubSpot.
* **HubSpot pop-up buttons** ("Request A Quote" buttons that opened a HubSpot pop-up) now go to
  the Request A Quote page. The "How much does a pool liner cost" image button now goes to the
  vinyl liner cost calculator. Check these are where you want them.
* **HubSpot-hosted videos** (pool opening highlight, safety cover video) are now standard video
  players using the original video files.
* **"Swimming Pool Resources" sections** now show your 3 newest blog posts. HubSpot filled these
  in with JavaScript.
* **Broken theme demo links fixed.** About 100 buttons, such as "Discover More" on the homepage,
  pointed to the theme vendor's demo site. They now point to the blog, the about page or the
  relevant service page.
* **Self-referencing canonical tags** were added to blog listing pages, which HubSpot left without one.
* **Footer** now shows your address, phone number and email.

## Already broken on the live site (not caused by the move)

These links point to pages that return 404 on HubSpot today. Fix them or remove them when you can:

* `/above-ground-pools/models/newtown`, `whitewood`, `vibesoho`, `athena`, `downtown`
  (linked from the above-ground pools page)
* `/pool-liners/cardinal` (linked from the pool liner cost blog post)
* `/inground-pool-installation-design/kitchener-waterloo-cambridge` (linked from the sanitizers blog post)

## Before you switch

1. **Export from HubSpot** while you still have access:
   * Contacts and deal history (CRM → Contacts → Export)
   * Form submissions (Marketing → Forms → each form → Export submissions)
   * Settings → Content → Domains & URLs → **URL Redirects → Export**. Compare the list with
     `src/data/redirects.json`. The crawl only finds redirects that something links to, so add
     any missing ones.
2. **Google Search Console**: confirm you have access to the `hipelpools.ca` property (a Domain
   property covers the blog too). Export *Pages → Indexed* and check that every URL in it exists
   in `dist/main/sitemap.xml` or `dist/blog/sitemap.xml`, or has a redirect.
3. **Set up Cloudflare Pages** (see README). Deploy, then click through the `*.pages.dev`
   preview: test a quote form submission end to end.

## Launch day

1. In HubSpot, **disconnect** `hipelpools.ca`, `www.hipelpools.ca` and `blog.hipelpools.ca`
   (Settings → Domains & URLs).
2. In Cloudflare Pages, add the custom domains (`hipelpools.ca` + `www` on the main project,
   `blog.hipelpools.ca` on the blog project). If your DNS is elsewhere, update the records it
   asks for.
3. Set `www.hipelpools.ca` to redirect to `hipelpools.ca` (Cloudflare → Rules → Redirect Rules,
   or a Bulk Redirect). HubSpot did the same.
4. Check, in a private browser window:
   * `https://hipelpools.ca`, a few service pages, a blog post
   * `https://hipelpools.ca/pool-service/pool-closing` → should redirect to `…/pool-closing/`
   * An old image URL such as `https://hipelpools.ca/hubfs/favicon-1.png` → should redirect to `/files/favicon-1.png`
   * Submit the quote form, and confirm the email arrives and the thank-you page shows
5. In **Search Console**: submit `https://hipelpools.ca/sitemap.xml` and
   `https://blog.hipelpools.ca/sitemap.xml`, and use *URL Inspection → Request indexing* on the
   homepage and your top 5 pages.
6. Check your **Google Business Profile** website link still points to `https://hipelpools.ca`.

## After launch

* Watch Search Console's *Pages* report daily for 2 weeks. Any spike in "Not found (404)"
  means a URL needs a redirect.
* Keep HubSpot active (even on the free tier) for ~2 weeks in case you need to look anything up.
  Then cancel the paid plan.
* A small ranking wobble for 1–2 weeks is normal after any platform move. Rankings normally
  recover fully because the URLs and content are unchanged, and the new site loads much faster.
