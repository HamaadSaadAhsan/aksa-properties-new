#!/usr/bin/env node
// Saves the CRM's published Properties into src/data/site.json, matched by unit code (units[].inv.code).
// The build reads the CRM itself when its key is set; this keeps the saved copy current for builds without one.
//
//   node tools/sync-crm.mjs           show what would change
//   node tools/sync-crm.mjs --write   write src/data/site.json
//
// Reads CRM_API_URL and CRM_API_KEY from the environment or .env.local (gitignored). Never prints the key.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { applyProperties, crmConfig, fetchProperties } from '../src/lib/crm.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dataPath = join(root, 'src/data/site.json');
const write = process.argv.includes('--write');

if (existsSync(join(root, '.env.local'))) {
  process.loadEnvFile(join(root, '.env.local'));
}
const config = crmConfig();
if (!config) {
  fail('Set CRM_API_URL and CRM_API_KEY (in .env.local or the environment).');
}

const data = JSON.parse(readFileSync(dataPath, 'utf8'));
const { changes, missing, extra, published } = await fetchProperties(config)
  .then((byCode) => applyProperties(data, byCode))
  .catch((error) => fail(error.message));

console.log(`CRM: ${published} published properties. Site: ${data.units.length} units.`);
console.log(`${changes.length} unit(s) change.`);
changes.forEach((line) => console.log(`  ${line}`));
if (missing.length) console.log(`${missing.length} unit(s) not published in the CRM, left as they are: ${preview(missing)}`);
if (extra.length) console.log(`${extra.length} CRM unit code(s) with no unit on the site: ${preview(extra)}`);

if (write && changes.length) {
  writeFileSync(dataPath, `${JSON.stringify(data, null, 2)}\n`);
  console.log('Wrote src/data/site.json.');
} else if (changes.length) {
  console.log('Dry run. Run with --write to save.');
}

function preview(items) {
  return items.length > 12 ? `${items.slice(0, 12).join(', ')} …` : items.join(', ');
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
