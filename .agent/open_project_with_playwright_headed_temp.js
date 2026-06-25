const { chromium } = require('playwright');

async function main() {
  const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:5000/';

  // Non-persistent context to avoid profile locking issues.
  const browser = await chromium.launch({
    headless: false,
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

  // Keep the process alive until the user closes the browser window.
  await page.waitForEvent('close');
  await browser.close();
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});

