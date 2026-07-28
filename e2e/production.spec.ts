import { expect, test } from "@playwright/test";

test("live search, audit, intensity, evidence, 3D, and card seam", async ({ page, request }) => {
  const health = await request.get("https://gitroast-ai.onrender.com/api/v1/health");
  expect(health.ok()).toBeTruthy();
  expect(await health.json()).toMatchObject({ status: "ok" });

  await page.goto("/");
  await expect(page.getByRole("link", { name: "GitHub" })).toHaveAttribute(
    "href",
    "https://github.com/NoorRattan/GitRoast.ai"
  );
  await page.getByLabel("GitHub profile link").fill("https://github.com/octocat");
  await page.getByRole("button", { name: "Audit profile" }).click();
  await expect(page).toHaveURL(/\/octocat$/);

  await expect(page.getByRole("heading", { name: "octocat", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why these scores moved" })).toBeVisible();
  await expect(page.getByText(/comparable profiles|profiles of similar account age/)).toBeVisible();

  const canvas = page.getByTestId("score-canvas");
  await expect(canvas).toBeVisible();
  await expect.poll(async () => canvas.evaluate((element) => {
    const target = element as HTMLCanvasElement;
    const gl = target.getContext("webgl2") ?? target.getContext("webgl");
    if (!gl) {
      return 0;
    }
    const pixels = new Uint8Array(target.width * target.height * 4);
    gl.readPixels(0, 0, target.width, target.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    let visiblePixels = 0;
    for (let index = 3; index < pixels.length; index += 4) {
      if (pixels[index] > 0) {
        visiblePixels += 1;
      }
    }
    return visiblePixels;
  })).toBeGreaterThan(100);

  const card = page.getByAltText("octocat GitRoast share card");
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

  await expect(page.getByRole("alert")).toContainText("Enter a GitHub username or a profile link");
});
