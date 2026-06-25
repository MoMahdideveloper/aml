/**
 * Playwright MCP browser_run_code template.
 * Replace RAW_COOKIES with in-memory cookie JSON.
 */
async (page) => {
  const RAW_COOKIES = [];

  const normalized = RAW_COOKIES.map((cookie) => {
    const sameSiteRaw = (cookie.sameSite || "").toLowerCase();
    let sameSite = "Lax";
    if (sameSiteRaw === "none" || sameSiteRaw === "no_restriction") sameSite = "None";
    if (sameSiteRaw === "strict") sameSite = "Strict";

    return {
      name: cookie.name,
      value: cookie.value,
      domain: cookie.domain,
      path: cookie.path || "/",
      expires: cookie.expirationDate ? Math.floor(cookie.expirationDate) : -1,
      httpOnly: Boolean(cookie.httpOnly),
      secure: Boolean(cookie.secure),
      sameSite
    };
  });

  await page.context().addCookies(normalized);
  await page.goto("https://gemini.google.com/app", { waitUntil: "domcontentloaded" });

  const url = page.url();
  const title = await page.title();
  const signInVisible = await page.locator("text=Sign in").first().isVisible().catch(() => false);

  return { url, title, authenticated: !signInVisible };
};

