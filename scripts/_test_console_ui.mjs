/**
 * Interactive smoke for Hive-served RealAI Console (/console).
 * Writes screenshots under ./screenshots/
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUT = join(ROOT, "screenshots");
mkdirSync(OUT, { recursive: true });

const URL = process.env.CONSOLE_URL || "http://127.0.0.1:8001/console";
const verdict = {
  ok: false,
  url: URL,
  steps: [],
  consoleErrors: [],
  pageErrors: [],
};

function step(name, detail) {
  verdict.steps.push({ name, ...detail, at: new Date().toISOString() });
}

const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const page = await context.newPage();

page.on("console", (msg) => {
  if (msg.type() === "error") verdict.consoleErrors.push(msg.text());
});
page.on("pageerror", (err) => verdict.pageErrors.push(String(err)));

try {
  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 15000 });
  await page.waitForTimeout(800);

  const title = await page.title();
  const nodeState = await page.locator("#nodeState").textContent();
  const bodyText = (await page.locator("body").innerText()).slice(0, 400);
  step("load", { title, nodeState, bodyPreview: bodyText.replace(/\s+/g, " ").slice(0, 200) });

  await page.screenshot({ path: join(OUT, "console-desktop.png"), fullPage: true });

  // Wait for probe to settle LIVE
  await page.waitForFunction(
    () => {
      const el = document.getElementById("nodeState");
      return el && (el.textContent || "").includes("LIVE");
    },
    null,
    { timeout: 5000 },
  ).catch(() => {});
  const afterProbe = await page.locator("#nodeState").textContent();
  step("probe", { nodeState: afterProbe });

  // New thread + send chat
  await page.click("#newChat");
  await page.fill("#input", "Reply with exactly: CONSOLE_UI_OK");
  await page.click("#send");

  // Wait for assistant bubble (send re-enabled + feed grows)
  await page.waitForFunction(
    () => {
      const send = document.getElementById("send");
      const feed = document.getElementById("feed");
      return send && !send.disabled && feed && feed.innerText.includes("CONSOLE_UI_OK");
    },
    null,
    { timeout: 120000 },
  );

  const feedText = await page.locator("#feed").innerText();
  const sendDisabled = await page.locator("#send").isDisabled();
  step("chat", {
    sendDisabled,
    feedHasPrompt: feedText.includes("CONSOLE_UI_OK"),
    feedPreview: feedText.replace(/\s+/g, " ").slice(0, 500),
  });

  await page.screenshot({ path: join(OUT, "console-after-chat.png"), fullPage: true });

  // Mobile viewport
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: join(OUT, "console-mobile.png"), fullPage: true });
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth };
  });
  step("mobile", overflow);

  verdict.ok =
    afterProbe === "LIVE" &&
    feedText.includes("CONSOLE_UI_OK") &&
    verdict.pageErrors.length === 0 &&
    !verdict.consoleErrors.some((e) => !/favicon/i.test(e));

  // Toggle speak
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.click("#voiceToggle");
  const voiceLabel = await page.locator("#voiceToggle").textContent();
  step("voice_toggle", { voiceLabel });
} catch (err) {
  verdict.error = String(err);
  try {
    await page.screenshot({ path: join(OUT, "console-error.png"), fullPage: true });
  } catch (_) {}
} finally {
  await browser.close();
}

const outJson = join(OUT, "console-verdict.json");
writeFileSync(outJson, JSON.stringify(verdict, null, 2));
console.log(JSON.stringify(verdict, null, 2));
process.exit(verdict.ok ? 0 : 1);
