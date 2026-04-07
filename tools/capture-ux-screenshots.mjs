/**
 * Capture UX audit screenshots for D-149 evidence.
 * Usage: node tools/capture-ux-screenshots.mjs
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { resolve } from 'path';

const BASE = 'http://localhost:4000';
const OUT = resolve('evidence/sprint-78/browser-audit/screenshot-evidence');
mkdirSync(OUT, { recursive: true });

const pages = [
  { id: 'UX-001', path: '/missions', desc: 'Missions error state' },
  { id: 'UX-002', path: '/health', desc: 'Health no retry' },
  { id: 'UX-003', path: '/agents', desc: 'Agent Health silent empty' },
  { id: 'UX-004', path: '/projects', desc: 'Projects contradictory states' },
  { id: 'UX-005', path: '/monitoring', desc: 'Monitoring mixed states' },
  { id: 'UX-006', path: '/missions', desc: 'Sidebar no tooltip (hover)' },
  { id: 'UX-007', path: '/missions', desc: 'SSE status misleading' },
];

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1520, height: 720 } });

  for (const p of pages) {
    const page = await ctx.newPage();
    await page.goto(`${BASE}${p.path}`, { waitUntil: 'networkidle', timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(2000);

    if (p.id === 'UX-006') {
      // Hover over first sidebar icon
      const sidebar = page.locator('nav a').first();
      await sidebar.hover().catch(() => {});
      await page.waitForTimeout(500);
    }

    if (p.id === 'UX-007') {
      // Zoom into top-right SSE indicator
      await page.screenshot({
        path: resolve(OUT, `${p.id}.png`),
        clip: { x: 0, y: 0, width: 1520, height: 720 },
      });
    } else {
      await page.screenshot({ path: resolve(OUT, `${p.id}.png`), fullPage: false });
    }

    console.log(`  ${p.id}: ${p.desc} -> ${p.id}.png`);
    await page.close();
  }

  await browser.close();
  console.log('Done. Screenshots in', OUT);
}

main().catch(e => { console.error(e); process.exit(1); });
