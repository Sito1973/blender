// Renderiza index.html a PDF (A4) con Chromium/Playwright.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const dir = path.resolve(process.argv[2] || __dirname);
  const out = path.resolve(process.argv[3] || path.join(dir, 'brochure.pdf'));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.join(dir, 'index.html'), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true });
  await browser.close();
  console.log('PDF:', out);
})();
