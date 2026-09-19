import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  // Go to the job run page, do not wait for networkidle
  try {
    await page.goto('https://github.com/LouSens/KerjaCerdas/actions/runs/35237338539/job/105256539046', { waitUntil: 'domcontentloaded', timeout: 30000 });
  } catch(e) {
    console.log("Goto error:", e.message);
  }
  
  // Wait for the log lines to appear
  try {
      await page.waitForSelector('.react-job-log-line', { timeout: 15000 });
  } catch(e) {
      console.log("Could not find log lines, printing full body text instead:");
      console.log(await page.locator('body').innerText());
      await browser.close();
      return;
  }
  
  // Extract all text from the log lines
  const logs = await page.locator('.react-job-log-line').allInnerTexts();
  console.log("LOG OUTPUT:");
  console.log(logs.join('\n'));
  
  await browser.close();
})();
