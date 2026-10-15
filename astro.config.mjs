// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';

// `site` is your live address. Astro uses it for canonical URLs and the sitemap.
export default defineConfig({
  site: 'https://gramsperdollar.com',
  trailingSlash: 'never',
  build: { format: 'file' }, // /about instead of /about/ — one clean URL per page
  integrations: [mdx(), sitemap({ filter: (page) => !page.includes('/write') })],
});
