// Sales facts from the CRM's public API, joined to the site's homes by unit code (units[].inv.code = the CRM record's title).
// Plans, shapes and media stay as they are; only status, price, areas, parking and orientation change.

// The site shows four states; the CRM has more.
const STATUS = {
  available: 'available',
  reserved: 'reserved',
  on_contract: 'sold',
  withheld: 'soon',
  sold: 'sold',
  deed_signed: 'sold',
};
const LABEL = { available: 'Available', reserved: 'Reserved', sold: 'Sold', soon: 'Coming soon' };

/** Reads CRM_API_URL and CRM_API_KEY from the environment. Never logs the key. */
export function crmConfig(env = process.env) {
  const base = (env.CRM_API_URL || '').replace(/\/+$/, '');
  const key = env.CRM_API_KEY || '';
  return base && key ? { base, key } : null;
}

/** Every published Property, keyed by its unit code. */
export async function fetchProperties({ base, key }) {
  const api = async (path) => {
    const response = await fetch(base + path, { headers: { Authorization: `Bearer ${key}`, Accept: 'application/json' } });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText} from ${path}${response.status === 401 ? ' (check CRM_API_KEY)' : ''}`);
    }
    return response.json();
  };

  const collections = (await api('/api/public/v1/collections')).data;
  if (!collections.some((c) => c.slug === 'properties')) {
    throw new Error(`This key can't read Properties. It can read: ${collections.map((c) => c.slug).join(', ') || 'nothing'}.`);
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
  return byCode;
}

/** Writes the CRM's facts onto data.units in place and reports what changed. */
export function applyProperties(data, byCode) {
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

  return { changes, missing, extra: [...byCode.keys()].filter((code) => !seen.has(code)), published: byCode.size };
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
