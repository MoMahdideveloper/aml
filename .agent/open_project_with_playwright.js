const { chromium } = require('playwright');

async function main() {
  const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:5000/';
  const userDataDir = process.env.PW_USER_DATA_DIR || 'C:\\\\antig-chrome';

  // Use a persistent context so it behaves like a Chrome profile session.
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });

  const page = context.pages()[0] || await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

  // Keep the process alive until the user closes the browser window.
  await page.waitForEvent('close');
  await context.close();
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});

