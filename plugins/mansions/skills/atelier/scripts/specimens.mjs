#!/usr/bin/env node
// Render the art direction specimens (assets/directions/*.html, page 1) to assets/directions/specimens/<id>.png
// and a contact sheet assets/directions/directions.png. Use it to SEE the directions before a genome is dealt.
//   node specimens.mjs [id ...]
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

function loadPlaywright() {
  for (const b of [path.join(process.cwd(), "noop.js"), import.meta.url]) {
    try { return createRequire(b)("playwright"); } catch {}
  }
  console.error("Playwright not found. In your project run: npm i -D playwright@1.63.0 && npx playwright install chromium");
  process.exit(2);
}
const { chromium } = loadPlaywright();
const here = path.dirname(fileURLToPath(import.meta.url));
const dir = path.resolve(here, "..", "assets", "directions");
const only = process.argv.slice(2);
const files = fs.readdirSync(dir).filter((f) => f.endsWith(".html") && !f.includes(".motion.") && (!only.length || only.includes(f.replace(".html", ""))));
fs.mkdirSync(path.join(dir, "specimens"), { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
for (const f of files) {
  await page.setViewportSize({ width: 1080, height: 1350 });
  await page.goto(pathToFileURL(path.join(dir, f)).href, { waitUntil: "networkidle" });
  const size = await page.evaluate(() => { const r = document.querySelector("section.page").getBoundingClientRect(); return { width: Math.round(r.width), height: Math.round(r.height) }; });
  if (size.width !== 1080 || size.height !== 1350) await page.setViewportSize(size);
  await page.evaluate(() => document.fonts.ready);
  if (await page.evaluate(() => typeof window.seek === "function")) await page.evaluate(() => window.seek(window.POSTER_T || 99));
  await (await page.$("section.page")).screenshot({ path: path.join(dir, "specimens", f.replace(".html", ".png")) });
  console.log("specimen:", f);
}
await browser.close();
execFileSync(process.platform === "win32" ? "python" : "python3",
  [path.join(here, "contact_sheet.py"), path.join(dir, "specimens"), "--pattern", "*.png", "--cols", "4", "--labels", "--out", path.join(dir, "directions.png")], { stdio: "inherit" });
