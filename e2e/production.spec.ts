import { expect, test } from "@playwright/test";
import { PNG } from "pngjs";

test("live search, audit, intensity, evidence, score visual, and card seam", async ({ page, request }) => {
  const apiBaseUrl = process.env.API_GATEWAY_BASE_URL ?? "https://gitroast-api-gateway-preview.jnoorrattan.workers.dev/api/v1";
  const health = await request.get(`${apiBaseUrl}/health`);
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toMatchObject({ status: "ok" });

  await page.goto("/");
  await page.waitForLoadState("domcontentloaded");
  const profileInput = page.getByLabel("GitHub profile link");
  await expect(profileInput).toBeVisible();

  const navToggle = page.getByRole("button", { name: /open navigation|close navigation/i });
  if (await navToggle.isVisible() && await navToggle.getAttribute("aria-expanded") !== "true") {
    await navToggle.click();
  }

  await expect(page.locator('a[href="https://github.com/NoorRattan/GitRoast.ai"]').first()).toHaveAttribute(
    "href",
    "https://github.com/NoorRattan/GitRoast.ai"
  );
  await profileInput.fill("https://github.com/octocat");
  await page.getByRole("button", { name: "Audit profile" }).click();
  await expect(page).toHaveURL(/\/octocat$/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();

  await expect(page.getByRole("heading", { name: /octocat/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /why these signals moved/i })).toBeVisible();
  const cohortRank = page.locator(".rank-metric");
  await expect(cohortRank).toHaveCount(1);
  await expect(cohortRank).toContainText(/comparable profiles|similar profiles/);

  const canvas = page.getByTestId("score-canvas");
  await expect(canvas).toBeVisible();
  await expect.poll(async () => {
    const image = PNG.sync.read(await canvas.screenshot());
    let visiblePixels = 0;
    for (let index = 0; index < image.data.length; index += 4) {
      const red = image.data[index];
      const green = image.data[index + 1];
      const blue = image.data[index + 2];
      const alpha = image.data[index + 3];
      if (alpha > 0 && Math.max(red, green, blue) > 80 && Math.max(red, green, blue) - Math.min(red, green, blue) > 16) {
        visiblePixels += 1;
      }
    }
    return visiblePixels;
  }).toBeGreaterThan(100);

  const card = page.getByAltText("octocat GitRoast share card");
  await card.scrollIntoViewIfNeeded();
  await expect(card).toBeVisible();
  await expect.poll(async () => card.evaluate((element) => (
    (element as HTMLImageElement).naturalWidth
  ))).toBeGreaterThan(0);

  await page.getByRole("tab", { name: "mild" }).click();
  await expect(page.getByText("Applied intensity: mild")).toBeVisible();
});

test("invalid profile input returns visible guidance", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("GitHub profile link").fill("https://example.com/not-github");
  await page.getByRole("button", { name: "Audit profile" }).click();

  await expect(page.locator(".search-error")).toContainText("Enter a GitHub username or a profile link");
});
