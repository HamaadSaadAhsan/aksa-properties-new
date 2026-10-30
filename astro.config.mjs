import { defineConfig } from 'astro/config';

// Static pages only. 'file' keeps the addresses the site already has (index.html, project.html) and gives each home
// homes/<code>.html. SITE_URL (e.g. https://aksaresidencies.pt) turns on canonical links and the sitemap.
export default defineConfig({
  site: process.env.SITE_URL || undefined,
  output: 'static',
  compressHTML: false,
  build: { format: 'file' },
});
