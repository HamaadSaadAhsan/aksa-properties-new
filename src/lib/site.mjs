// The site's data at build time: src/data/site.json (shapes, plans, media, last synced sales facts), with the CRM's
// current sales facts on top when CRM_API_URL and CRM_API_KEY are set. A set key that fails stops the build, so a
// deploy never goes out with prices nobody checked.
import { existsSync, readFileSync } from 'node:fs';
import { applyProperties, crmConfig, fetchProperties } from './crm.mjs';

if (existsSync('.env.local')) process.loadEnvFile('.env.local');

let loading;

export function loadSite() {
  return (loading ??= (async () => {
    const data = JSON.parse(readFileSync('src/data/site.json', 'utf8'));
    const config = crmConfig();
    if (!config) {
      console.warn('[site] CRM_API_URL / CRM_API_KEY not set: using the sales facts saved in src/data/site.json.');
      return data;
    }
    const { changes, missing, published } = applyProperties(data, await fetchProperties(config));
    console.log(`[site] CRM: ${published} published properties, ${changes.length} home(s) differ from site.json, ${missing.length} not published.`);
    return data;
  })());
}

/** A home's address: its sales code, lower case (B0D → /homes/b0d). */
export const homeSlug = (unit) => String(unit.inv?.code ?? unit.id).toLowerCase();
