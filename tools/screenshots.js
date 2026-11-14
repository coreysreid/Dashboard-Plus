// Drive a browser through a list of steps and save screenshots.
// Called by tools/make_screenshots.py, which writes the steps; not run on its own.
// Usage: node tools/screenshots.js <steps.json>
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
  const plan = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch(plan.executablePath ? { executablePath: plan.executablePath } : {});
  const page = await browser.newPage({ viewport: { width: plan.width, height: plan.height }, deviceScaleFactor: 1,
    locale: plan.locale || 'en-AU', timezoneId: plan.timezone || 'UTC' });
  const base = plan.base.replace(/\/$/, '');
  try {
    for (const step of plan.steps) {
      if (step.goto) await page.goto(base + step.goto);
      if (step.fill) await page.fill(step.fill, String(step.value));
      if (step.select) await page.selectOption(step.select, String(step.value));
      if (step.check) await page.setChecked(step.check, step.value !== false);
      if (step.click) await page.click(step.click);
      if (step.submit) await Promise.all([page.waitForNavigation(), page.click(step.submit)]);
      if (step.media) await page.emulateMedia({ media: step.media });
      if (step.pages) {
        // Count the printed pages on both common paper sizes.
        for (const format of ['A4', 'Letter']) {
          const pdf = (await page.pdf({ format, printBackground: true })).toString('latin1');
          console.log(`pages ${step.pages} ${format} ${(pdf.match(/\/Type\s*\/Page[^s]/g) || []).length}`);
        }
      }
      if (step.shot) {
        // Show folders the way they look on Windows, so screenshots match the portable folder.
        await page.evaluate((swaps) => {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            for (const [from, to] of swaps) node.nodeValue = node.nodeValue.split(from).join(to);
          }
        }, plan.swaps || []);
        await page.screenshot({ path: step.shot, fullPage: true });
        console.log('saved ' + step.shot);
      }
    }
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exit(1); });
