# Grams per Dollar

High-protein meal prep, priced by the gram. Static site built with Astro.

## Run it on your computer (optional)
1. Install Node.js (LTS) from nodejs.org.
2. In this folder: `npm install`, then `npm run dev`. Open http://localhost:4321.

## Where things live
- `src/layouts/Base.astro` — the SEO basics for every page (title, description, canonical URL).
- `src/pages/` — one file = one page. `about.astro` becomes `/about`.
- `public/robots.txt` — tells search engines they may crawl the site and where the sitemap is.
- The sitemap (`/sitemap-index.xml`) is generated automatically on every build.

## Deploy settings (Cloudflare)
- Build command: `npm run build`
- Output folder: `dist`
