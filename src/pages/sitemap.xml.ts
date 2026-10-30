import type { APIContext } from 'astro';
import { homeSlug, loadSite } from '../lib/site.mjs';

// Only with SITE_URL: a sitemap needs absolute addresses.
export async function GET({ site }: APIContext) {
  if (!site) {
    return new Response(null, { status: 404 });
  }
  const { units } = await loadSite();
  const paths = ['index.html', 'project.html', ...units.map((unit) => `homes/${homeSlug(unit)}.html`)];
  const urls = paths.map((path) => `<url><loc>${new URL(path, site).href}</loc></url>`).join('');
  return new Response(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>\n`, {
    headers: { 'Content-Type': 'application/xml' },
  });
}
