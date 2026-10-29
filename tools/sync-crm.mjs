#!/usr/bin/env node
// Pulls the published Properties from the CRM's public API into data.json, matched by unit code (units[].inv.code).
// Plans, shapes and media stay as they are; only sales facts change: status, price, areas, parking, orientation.
//
//   node tools/sync-crm.mjs           show what would change
//   node tools/sync-crm.mjs --write   write data.json
//
// Reads CRM_API_URL and CRM_API_KEY from the environment or .env.local (gitignored). Never prints the key.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dataPath = join(root, 'data.json');
const write = process.argv.includes('--write');

if (existsSync(join(root, '.env.local'))) {
  process.loadEnvFile(join(root, '.env.local'));
}
const base = (process.env.CRM_API_URL || '').replace(/\/+$/, '');
const key = process.env.CRM_API_KEY || '';
if (!base || !key) {
  fail('Set CRM_API_URL and CRM_API_KEY (in .env.local or the environment).');
}

// The site shows three states; the CRM has six.
const STATUS = {
  available: 'available',
  reserved: 'reserved',
  on_contract: 'reserved',
  withheld: 'reserved',
  sold: 'sold',
  deed_signed: 'sold',
};
const LABEL = { available: 'Available', reserved: 'Reserved', sold: 'Sold' };

const collections = (await api('/api/public/v1/collections')).data;
const properties = collections.find((c) => c.slug === 'properties');
if (!properties) {
  fail(`This key can't read Properties. It can read: ${collections.map((c) => c.slug).join(', ') || 'nothing'}.`);
}

const records = [];
for (let cursor = null; ; ) {
  const page = await api(`/api/public/v1/collections/properties/records?limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`);
  records.push(...page.data);
  cursor = page.meta.next_cursor;
  if (!cursor) break;
}

const byCode = new Map();
for (const record of records) {
  const code = String(record.title ?? record.values.name ?? '').trim().toUpperCase();
  if (code) byCode.set(code, record.values);
}

const data = JSON.parse(readFileSync(dataPath, 'utf8'));
const changes = [];
const missing = [];
const seen = new Set();

for (const unit of data.units) {
  const code = String(unit.inv?.code ?? '').toUpperCase();
  const v = byCode.get(code);
  if (!v) {
    missing.push(unit.id);
    continue;
  }
  seen.add(code);

  const status = STATUS[scalar(v.status)] ?? unit.status;
  const price = number(v.list_price);
  const next = {
    status,
    price,
    inv: {
      ...unit.inv,
      status: LABEL[status],
      typology: scalar(v.typology)?.toUpperCase() ?? unit.inv.typology,
      duplex: v.duplex ?? unit.inv.duplex,
      gross: number(v.gross_area),
      living: number(v.living_area),
      balc_ext: number(v.balcony_ext_area),
      balc_int: number(v.balcony_int_area),
      terrace: number(v.terrace_area),
      outdoor: number(v.outdoor_area),
      total: number(v.total_area),
      parking: number(v.parking_slots),
      orientation: orientation(unit.inv.orientation, list(v.orientation).map(title)),
      price,
    },
  };

  const diff = [];
  for (const field of ['status', 'price']) {
    if (unit[field] !== next[field]) diff.push(`${field} ${show(unit[field])} → ${show(next[field])}`);
  }
  for (const [field, value] of Object.entries(next.inv)) {
    if (unit.inv[field] !== value) diff.push(`inv.${field} ${show(unit.inv[field])} → ${show(value)}`);
  }
  if (diff.length) {
    changes.push(`${unit.id} (${code}): ${diff.join(', ')}`);
    Object.assign(unit, next);
  }
}

const extra = [...byCode.keys()].filter((code) => !seen.has(code));

console.log(`CRM: ${records.length} published properties. Site: ${data.units.length} units.`);
console.log(`${changes.length} unit(s) change.`);
changes.forEach((line) => console.log(`  ${line}`));
if (missing.length) console.log(`${missing.length} unit(s) not published in the CRM, left as they are: ${preview(missing)}`);
if (extra.length) console.log(`${extra.length} CRM unit code(s) with no unit on the site: ${preview(extra)}`);

if (write && changes.length) {
  writeFileSync(dataPath, JSON.stringify(data));
  // index.html carries its own copy of data.json, as build_inventory.py writes it.
  const indexPath = join(root, 'index.html');
  const html = readFileSync(indexPath, 'utf8');
  const open = '<script id="manifest" type="application/json">';
  const start = html.indexOf(open) + open.length;
  const end = html.indexOf('</script>', start);
  writeFileSync(indexPath, html.slice(0, start) + JSON.stringify(data).replace(/<\//g, '<\\/') + html.slice(end));
  console.log('Wrote data.json and the copy in index.html.');
} else if (changes.length) {
  console.log('Dry run. Run with --write to save.');
}

async function api(path) {
  const response = await fetch(base + path, { headers: { Authorization: `Bearer ${key}`, Accept: 'application/json' } });
  if (!response.ok) {
    fail(`${response.status} ${response.statusText} from ${path}${response.status === 401 ? ' (check CRM_API_KEY)' : ''}`);
  }
  return response.json();
}

// Select and status values may come as the option value or as {value}.
function scalar(value) {
  if (value == null || value === '') return null;
  return typeof value === 'object' ? (value.value ?? null) : String(value);
}

function list(value) {
  return (Array.isArray(value) ? value : value == null ? [] : [value]).map(scalar).filter(Boolean);
}

// Currency values may come as a number or as {amount}.
function number(value) {
  if (value != null && typeof value === 'object') value = value.amount ?? value.value;
  if (value == null || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

// Keeps the site's wording when the CRM has the same directions in another order.
function orientation(current, directions) {
  const same = current && current.split(' / ').sort().join() === [...directions].sort().join();
  return same ? current : directions.join(' / ') || null;
}

function title(word) {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function show(value) {
  return value == null ? '–' : JSON.stringify(value);
}

function preview(items) {
  return items.length > 12 ? `${items.slice(0, 12).join(', ')} …` : items.join(', ');
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
