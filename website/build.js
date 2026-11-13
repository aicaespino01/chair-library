// Builds "Chair Website.html" from the chair files in ../chairs.
// Run from anywhere:  node website/build.js
// Text shown on the website is copied exactly from the chair files.
// The numbers worked out here are only used for sorting, filtering and "Find my chair".

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const CHAIRS_DIR = path.join(ROOT, 'chairs');
const TEMPLATE = path.join(__dirname, 'template.html');
const OUT = path.join(ROOT, 'Chair Website.html');

// ---------- small markdown renderer (only what the chair files use) ----------

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function linkify(t) {
  return t.replace(/https?:\/\/(?:(?!&quot;|&lt;|&gt;)[^\s<>"])+/g, (url) => {
    let trail = '';
    while (/[.,;:!?)\]]$/.test(url)) {
      const opens = (url.match(/\(/g) || []).length;
      const closes = (url.match(/\)/g) || []).length;
      if (url.endsWith(')') && opens >= closes) break;
      trail = url.slice(-1) + trail;
      url = url.slice(0, -1);
    }
    return `<a href="${url}" target="_blank" rel="noopener">${url}</a>${trail}`;
  });
}

function inline(s) {
  return s
    .split(/(`[^`]*`)/)
    .map((part) => {
      if (part.length >= 2 && part.startsWith('`') && part.endsWith('`')) {
        return '<code>' + esc(part.slice(1, -1)) + '</code>';
      }
      let t = esc(part);
      t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      return linkify(t);
    })
    .join('');
}

function splitRow(r) {
  let s = r.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|')) s = s.slice(0, -1);
  return s.split('|').map((c) => c.trim());
}

const isSepRow = (r) => /^\s*\|?\s*:?-{2,}/.test(r);
const LIST_RE = /^\s*([-*]|\d+\.)\s+/;

function renderTable(rows) {
  const head = splitRow(rows[0]);
  let body = rows.slice(1);
  if (body.length && isSepRow(body[0])) body = body.slice(1);
  const th = head.map((c) => `<th>${inline(c)}</th>`).join('');
  const trs = body
    .map((r) => {
      const cells = splitRow(r);
      return '<tr>' + cells.map((c, i) => `<td data-label="${esc(head[i] || '')}">${inline(c)}</td>`).join('') + '</tr>';
    })
    .join('');
  return `<div class="table-wrap"><table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table></div>`;
}

function md(src) {
  const lines = src.replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    let m = l.match(/^(#{1,6})\s+(.*)$/);
    if (m) {
      const n = Math.min(m[1].length + 1, 6); // page already has its own h1
      out.push(`<h${n}>${inline(m[2])}</h${n}>`);
      i++;
      continue;
    }
    if (/^\s*\|/.test(l)) {
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]);
      out.push(renderTable(rows));
      continue;
    }
    if (LIST_RE.test(l)) {
      const ordered = /^\s*\d+\./.test(l);
      const start = ordered ? parseInt(l.trim(), 10) : 1;
      const items = [];
      while (i < lines.length && LIST_RE.test(lines[i])) {
        items.push(lines[i].replace(LIST_RE, ''));
        i++;
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !LIST_RE.test(lines[i])) {
          items[items.length - 1] += ' ' + lines[i].trim();
          i++;
        }
      }
      const tag = ordered ? 'ol' : 'ul';
      const startAttr = ordered && start !== 1 ? ` start="${start}"` : '';
      out.push(`<${tag}${startAttr}>` + items.map((x) => `<li>${inline(x)}</li>`).join('') + `</${tag}>`);
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^#{1,6}\s/.test(lines[i]) && !/^\s*\|/.test(lines[i]) && !LIST_RE.test(lines[i])) {
      para.push(lines[i].trim());
      i++;
    }
    out.push('<p>' + inline(para.join(' ')) + '</p>');
  }
  return out.join('\n');
}

// ---------- reading one chair file ----------

function parseTopBlock(name, block) {
  const fields = {};
  const order = [];
  for (const line of block.split('\n')) {
    if (!line.trim()) continue;
    const m = line.match(/^([a-z_]+):\s?(.*)$/);
    if (!m) throw new Error(`${name}: cannot read this top-block line: ${line}`);
    let v = m[2].trim();
    if (v.length >= 2 && v.startsWith('"') && v.endsWith('"')) v = v.slice(1, -1);
    fields[m[1]] = v;
    order.push(m[1]);
  }
  return { fields, order };
}

const leadNum = (s) => {
  const m = (s || '').match(/^(\d+(?:\.\d+)?)/);
  return m ? parseFloat(m[1]) : null;
};

// "42.0-51.2" or "42.5-49.5 (VC2)" -> {min, max, text:"42.0-51.2"}; anything else -> nulls
function range(s) {
  const m = (s || '').match(/^(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)/);
  if (m) return { min: parseFloat(m[1]), max: parseFloat(m[2]), text: m[0] };
  const n = (s || '').match(/^(\d+(?:\.\d+)?)/);
  if (n) return { min: parseFloat(n[1]), max: parseFloat(n[1]), text: n[0] };
  return { min: null, max: null, text: null };
}

function depthSlide(v) {
  const s = (v || '').toLowerCase();
  if (/^yes/.test(s)) return 'yes';
  if (/^not listed/.test(s)) return 'not listed';
  if (/^not/.test(s)) return 'unknown';
  if (/^no\b/.test(s)) return 'no';
  return 'unknown';
}

function arms(v) {
  const s = (v || '').toLowerCase();
  if (/^none/.test(s)) return 'no';
  if (/^not known/.test(s) || !s) return 'unknown';
  if (/\bnone\b/.test(s)) return 'both';
  return 'yes';
}

function back(v) {
  const s = (v || '').toLowerCase();
  if (s.includes('not clear')) return 'unclear';
  if (s.includes('mesh')) return 'mesh';
  if (s.includes('fabric')) return 'fabric';
  return 'unknown';
}

function identified(v) {
  const s = (v || '').toLowerCase().trim();
  if (s.startsWith('confirmed')) return 'confirmed';
  if (s.startsWith('very likely')) return 'very likely';
  return 'unsure';
}

function whereToBuy(sectionMd) {
  const rows = sectionMd.split('\n').filter((l) => /^\s*\|/.test(l));
  if (rows.length < 2) return [];
  const head = splitRow(rows[0]).map((h) => h.toLowerCase());
  const col = (name) => head.findIndex((h) => h.startsWith(name));
  const iShop = col('shop'), iLink = col('link'), iPrice = col('price'), iBranch = col('branch'), iStock = col('in stock');
  return rows
    .slice(1)
    .filter((r) => !isSepRow(r))
    .map((r) => {
      const c = splitRow(r);
      const shop = c[iShop] || '';
      const branch = c[iBranch] || '';
      const stock = c[iStock] || '';
      const urlMatch = r.match(/https?:\/\/[^\s|)]+/);
      let place = null;
      if (/^office busters/i.test(shop)) {
        place = branch === '—' || branch === '-' || !branch || /^branch not stated/i.test(branch)
          ? 'OB (branch not stated)'
          : branch.split(',')[0].trim();
      } else if (/lazada ph|shopee ph/i.test(shop)) {
        place = 'Online (PH shops)';
      }
      return {
        shop,
        link: c[iLink] || '',
        url: urlMatch ? urlMatch[0] : null,
        price: c[iPrice] || '',
        branch,
        stock,
        inStock: /^yes/i.test(stock),
        place,
        isOB: /^office busters/i.test(shop),
      };
    });
}

function readChair(file) {
  const raw = fs.readFileSync(path.join(CHAIRS_DIR, file), 'utf8').replace(/\r\n/g, '\n');
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) throw new Error(`${file}: no top block between --- lines`);
  const { fields: f, order } = parseTopBlock(file, m[1]);
  const body = m[2];

  const titleMatch = body.match(/^# (.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : `${f.brand} ${f.model}`;
  const afterTitle = titleMatch ? body.slice(body.indexOf(titleMatch[0]) + titleMatch[0].length) : body;
  const parts = afterTitle.split(/^## /m);
  const intro = parts.shift();
  const sections = parts.map((p) => {
    const nl = p.indexOf('\n');
    const heading = (nl === -1 ? p : p.slice(0, nl)).trim();
    const content = nl === -1 ? '' : p.slice(nl + 1);
    return { heading, content };
  });

  const wtbSection = sections.find((s) => /^where to buy/i.test(s.heading));
  const shops = wtbSection ? whereToBuy(wtbSection.content) : [];
  const photos = [...new Set((body.match(/https:\/\/cdn\.shopify\.com\/[^\s)|>]+/g) || []).map((u) => u.replace(/[.,;]+$/, '')))];

  const seat = range(f.seat_height_cm);
  const depth = range(f.seat_depth_cm);
  const priceText = f.lowest_price_seen_php || '';
  const priceMatch = priceText.match(/^(\d[\d,]*(?:\.\d+)?)/);
  const price = priceMatch ? parseFloat(priceMatch[1].replace(/,/g, '')) : null;
  const priceNote = priceMatch ? priceText.slice(priceMatch[0].length).trim() : priceText;
  const places = [...new Set(shops.filter((s) => s.place).map((s) => s.place))];
  const sitTest = [...new Set(shops.filter((s) => s.isOB && s.inStock).map((s) => s.place))];

  const brandShort = (f.brand || 'unknown').split(' (')[0].trim();

  const firstUrl = shops.map((s) => s.url).find(Boolean) || null;

  return {
    id: f.id || file.replace(/\.md$/, ''),
    file: `chairs/${file}`,
    title,
    fields: f,
    order,
    introHtml: md(intro),
    sections: sections.map((s) => ({ heading: s.heading, html: md(s.content) })),
    shops,
    photos,
    shopUrl: firstUrl,
    d: {
      brand: brandShort,
      seatMin: seat.min,
      seatMax: seat.max,
      seatText: seat.text,
      depthMin: depth.min,
      depthText: depth.text,
      price,
      priceNote,
      weightLimit: leadNum(f.weight_limit_kg),
      depthSlide: depthSlide(f.seat_depth_slide),
      arms: arms(f.armrests),
      back: back(f.back),
      identified: identified(f.identified),
      places,
      sitTest,
    },
    search: [title, ...order.map((k) => f[k]), ...shops.map((s) => `${s.shop} ${s.branch} ${s.price}`)].join(' \n ').toLowerCase(),
  };
}

// ---------- build ----------

const files = fs.readdirSync(CHAIRS_DIR).filter((f) => f.toLowerCase().endsWith('.md')).sort();
const chairs = files.map(readChair);

const checked = chairs.map((c) => c.fields.last_checked).filter(Boolean).sort();
const pad = (n) => String(n).padStart(2, '0');
const now = new Date();
const data = {
  builtOn: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
  checkedFrom: checked[0] || null,
  checkedTo: checked[checked.length - 1] || null,
  chairs,
};

// Escape "<" and two invisible line-break characters so the data can sit safely inside a <script> tag
const BS = String.fromCharCode(92);
const json = JSON.stringify(data)
  .split('<').join(BS + 'u003c')
  .split(String.fromCharCode(0x2028)).join(BS + 'u2028')
  .split(String.fromCharCode(0x2029)).join(BS + 'u2029');
const template = fs.readFileSync(TEMPLATE, 'utf8');
if (!template.includes('/*__CHAIR_DATA__*/')) throw new Error('template.html is missing the /*__CHAIR_DATA__*/ marker');
const html = template.replace('/*__CHAIR_DATA__*/', () => `window.CHAIR_DATA = ${json};`);
fs.writeFileSync(OUT, html, 'utf8');

// Summary so the numbers can be checked against the files
console.log(`Built: ${OUT}`);
console.log(`Chair files: ${files.length}, chairs on the website: ${chairs.length}`);
const show = (v) => (v === null || v === undefined ? '-' : String(v));
for (const c of chairs) {
  const d = c.d;
  console.log(
    [c.id.padEnd(46), `seat ${show(d.seatMin)}-${show(d.seatMax)}`.padEnd(14), `depth ${show(d.depthMin)}`.padEnd(11), `P${show(d.price)}`.padEnd(7),
      `wl ${show(d.weightLimit)}`.padEnd(7), `slide ${d.depthSlide}`.padEnd(17), `arms ${d.arms}`.padEnd(12), `back ${d.back}`.padEnd(13),
      d.identified.padEnd(12), `photos ${c.photos.length}`.padEnd(10), d.places.join(' / ')].join(' ')
  );
}
