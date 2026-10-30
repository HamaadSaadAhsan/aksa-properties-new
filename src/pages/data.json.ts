import { loadSite } from '../lib/site.mjs';

// What the 3D explorer and the project page read in the browser: site.json with the CRM's sales facts on top.
export async function GET() {
  return new Response(JSON.stringify(await loadSite()), { headers: { 'Content-Type': 'application/json' } });
}
