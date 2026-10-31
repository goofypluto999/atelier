#!/usr/bin/env node
// Draft a brand file from a live website: the real colours, fonts and logo, not a guess.
//   node brand_extract.mjs https://example.com [--out brand]
// Writes <out>/desktop.png and mobile.png (screenshots), logo files it can find, brand-draft.css (the token roles
// tokens.css uses) and brand-report.md (palette with area shares, fonts, contrast of the key pairs).
// Use only on sites you have permission to study. Review the draft by eye: the brand's own guide always wins.
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

function loadPlaywright() {
  for (const b of [path.join(process.cwd(), "noop.js"), import.meta.url]) {
    try { return createRequire(b)("playwright"); } catch {}
  }
  console.error("Playwright not found. In your project run: npm i -D playwright@1.63.0 && npx playwright install chromium");
  process.exit(2);
}
const { chromium } = loadPlaywright();
const args = process.argv.slice(2);
const url = args.find((a) => /^https?:\/\//.test(a));
if (!url) { console.error("usage: node brand_extract.mjs https://example.com [--out brand]"); process.exit(2); }
const out = path.resolve(args.includes("--out") ? args[args.indexOf("--out") + 1] : "brand");
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: path.join(out, "desktop.png"), fullPage: false });

const data = await page.evaluate(() => {
  const rgb = (s) => { const m = s && s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return v.length > 3 && v[3] < 0.5 ? null : [v[0], v[1], v[2]]; };
  const hex = (c) => "#" + c.map((x) => Math.round(x).toString(16).padStart(2, "0")).join("");
  const bg = {}, fg = {}, fonts = {}, marks = {};
  const vw = innerWidth, vh = innerHeight * 3;
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.top > vh) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none") continue;
    const b = rgb(cs.backgroundColor);
    if (b) bg[hex(b)] = (bg[hex(b)] || 0) + Math.min(r.width, vw) * Math.min(r.height, vh);
    for (const prop of ["borderTopColor", "borderLeftColor", "outlineColor", "fill", "stroke"]) {
      const c = rgb(cs[prop]);
      const w = prop.startsWith("border") ? parseFloat(cs[prop.replace("Color", "Width")]) : 1;
      if (c && w > 0 && (prop === "fill" || prop === "stroke" ? el.closest("svg") : true)) marks[hex(c)] = (marks[hex(c)] || 0) + 1;
    }
    const own = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim();
    if (own) {
      const f = rgb(cs.color);
      if (f) fg[hex(f)] = (fg[hex(f)] || 0) + own.length;
      const fam = cs.fontFamily.split(",")[0].replace(/["']/g, "").trim();
      fonts[fam] = (fonts[fam] || 0) + own.length;
    }
  }
  const bodyBg = rgb(getComputedStyle(document.body).backgroundColor) || rgb(getComputedStyle(document.documentElement).backgroundColor) || [255, 255, 255];
  bg[hex(bodyBg)] = (bg[hex(bodyBg)] || 0) + vw * vh;
  const pick = (sel) => { const e = document.querySelector(sel); if (!e) return null; const cs = getComputedStyle(e); return { family: cs.fontFamily, size: cs.fontSize, weight: cs.fontWeight, tracking: cs.letterSpacing, leading: cs.lineHeight }; };
  const logos = [];
  for (const el of document.querySelectorAll("header img, nav img, a img, img, svg")) {
    const id = `${el.id} ${el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className} ${el.getAttribute("alt") || ""} ${el.getAttribute("aria-label") || ""}`.toLowerCase();
    const inHead = !!el.closest("header, nav");
    if (!/logo|brand/.test(id) && !(inHead && logos.length < 2)) continue;
    if (el.tagName.toLowerCase() === "svg") logos.push({ type: "svg", markup: el.outerHTML.slice(0, 200000) });
    else if (el.currentSrc || el.src) logos.push({ type: "img", src: el.currentSrc || el.src });
    if (logos.length >= 4) break;
  }
  return { bg, fg, fonts, marks, h1: pick("h1"), h2: pick("h2"), p: pick("p"), button: pick("button, .button, a[class*=btn]"), logos, title: document.title };
});
await page.setViewportSize({ width: 390, height: 844 });
await page.screenshot({ path: path.join(out, "mobile.png") });

const logoFiles = [];
for (const [i, l] of data.logos.entries()) {
  try {
    if (l.type === "svg") { const f = `logo-${i + 1}.svg`; fs.writeFileSync(path.join(out, f), l.markup); logoFiles.push(f); }
    else {
      const res = await ctx.request.get(l.src);
      if (res.ok()) { const ext = (l.src.split("?")[0].match(/\.(png|svg|jpe?g|webp|gif)$/i) || [, "png"])[1]; const f = `logo-${i + 1}.${ext}`; fs.writeFileSync(path.join(out, f), await res.body()); logoFiles.push(f); }
    }
  } catch {}
}
await browser.close();

const toRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const L = (h) => { const [r, g, b] = toRgb(h); return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b); };
const ratio = (a, b) => { const x = L(a), y = L(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
const sat = (h) => { const [r, g, b] = toRgb(h).map((v) => v / 255); const mx = Math.max(r, g, b), mn = Math.min(r, g, b); return mx === 0 ? 0 : (mx - mn) / mx; };
const sortBy = (o) => Object.entries(o).sort((a, b) => b[1] - a[1]);
const bgs = sortBy(data.bg), fgs = sortBy(data.fg);
const totalBg = bgs.reduce((s, [, v]) => s + v, 0) || 1;
const notes = [];
const darkFound = bgs.map(([h]) => h).filter((h) => L(h) < 0.08)[0];
const lightFound = bgs.map(([h]) => h).filter((h) => L(h) > 0.6)[0];
const dark = darkFound || "#141414";
const light = lightFound || "#f4f2ed";
if (!darkFound) notes.push("No dark ground on the site: --night is a neutral placeholder.");
if (!lightFound) notes.push("No light ground on the site: --paper and --ink are neutral placeholders; decide whether the brand has a light mode at all.");
const inkOn = (ground) => {
  const best = fgs.map(([h]) => h).sort((a, b) => ratio(b, ground) - ratio(a, ground))[0];
  return best && ratio(best, ground) >= 4.5 ? best : (L(ground) > 0.5 ? "#1d1d1f" : "#f4f2ed");
};
const marks = sortBy(data.marks);
const accentFound = [...bgs, ...fgs, ...marks].map(([h]) => h).filter((h) => sat(h) > 0.25 && L(h) > 0.01 && L(h) < 0.75)[0];
const accent = accentFound || "#8a8f96";
if (!accentFound) notes.push("No saturated accent found in grounds, text, borders or SVG marks: --house is grey; set the brand accent by hand.");
const fam = (f) => (f ? `"${f.family.split(",")[0].replace(/["']/g, "").trim()}", system-ui, sans-serif` : "system-ui, sans-serif");
const css = `/* Draft brand tokens from ${url} (${new Date().toISOString().slice(0, 10)}). Review by eye, check with render.mjs --audit,
   and replace anything the brand guide says differently. Load after tokens.css. */
:root {
  --night: ${dark}; --deep: ${dark};
  --cream: ${inkOn(dark)}; --cream-2: ${inkOn(dark)}; --steel: #8a8f96;
  --paper: ${light}; --paper-2: ${light};
  --ink: ${inkOn(light)}; --ink-2: ${inkOn(light)};
  --house: ${accent}; --teal: ${accent}; --teal-lit: ${accent};
  --disp: ${fam(data.h1 || data.h2)};
  --body: ${fam(data.p)};
}
`;
fs.writeFileSync(path.join(out, "brand-draft.css"), css);
const rows = bgs.slice(0, 8).map(([h, v]) => `| ${h} | ground | ${Math.round((100 * v) / totalBg)}% |`).concat(fgs.slice(0, 6).map(([h, v]) => `| ${h} | text | ${v} chars |`), marks.slice(0, 6).map(([h, v]) => `| ${h} | border or drawing | ${v} uses |`));
const pairs = [[inkOn(light), light], [inkOn(dark), dark], [accent, light], [accent, dark]].map(([a, b]) => `| ${a} on ${b} | ${ratio(a, b).toFixed(1)}:1 |`);
fs.writeFileSync(path.join(out, "brand-report.md"), `# Brand draft: ${data.title || url}

Source: ${url}. Screenshots: desktop.png, mobile.png. Logos found: ${logoFiles.join(", ") || "none (add them by hand)"}.

${notes.length ? "## Notes\n" + notes.map((n) => "- " + n).join("\n") + "\n\n" : ""}## Palette (by area on screen, by amount of text, and by borders and drawing marks)
| colour | used as | share |
|---|---|---|
${rows.join("\n")}

## Type
- headings: ${JSON.stringify(data.h1 || data.h2)}
- body: ${JSON.stringify(data.p)}
- buttons: ${JSON.stringify(data.button)}
- faces by amount of text: ${sortBy(data.fonts).slice(0, 5).map(([f, n]) => `${f} (${n})`).join(", ")}

## Contrast of the drafted pairs (WCAG; 4.5:1 for text under 48 px on a 1080 canvas)
| pair | ratio |
|---|---|
${pairs.join("\n")}

## Next
1. Check the draft against the screenshots; fix roles that look wrong (the accent is the most saturated frequent colour, which is not always the brand's accent).
2. Get the fonts licensed for this use (python get_font.py "<Family>" for Google Fonts), and write brand.md: voice in three adjectives, what the brand never does.
`);
console.log(`brand draft: ${out} (brand-draft.css, brand-report.md, desktop.png, mobile.png, ${logoFiles.length} logo file(s))`);
