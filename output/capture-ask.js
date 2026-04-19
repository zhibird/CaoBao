const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  let askRequestBody = null;
  let askResponseBody = null;
  let askStatus = null;

  page.on('request', (request) => {
    if (request.url().includes('/api/v1/chat/ask')) {
      askRequestBody = request.postDataJSON();
    }
  });

  page.on('response', async (response) => {
    if (response.url().includes('/api/v1/chat/ask')) {
      askStatus = response.status();
      askResponseBody = await response.text();
    }
  });

  await page.goto('http://127.0.0.1:8765/', { waitUntil: 'networkidle' });
  if (!(await page.locator('#authModal').isVisible())) {
    await page.click('#railSettingsBtn');
  }
  const userId = `capture_${Date.now()}`;
  await page.click('#authRegisterTab');
  await page.fill('#registerUserIdInput', userId);
  await page.fill('#registerDisplayNameInput', 'Capture User');
  await page.fill('#registerPasswordInput', 'smoketest123');
  await page.fill('#registerConfirmPasswordInput', 'smoketest123');
  await Promise.all([
    page.waitForResponse((response) => response.url().includes('/api/v1/auth/register') && response.status() === 201),
    page.click('#registerAuthBtn'),
  ]);
  await page.click('#railNewChatBtn');
  await page.click('#toggleImportBtn');
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.click('#uploadFileBtn'),
  ]);
  await chooser.setFiles(path.resolve('README.md'));
  await page.click('#railFilesBtn');
  await page.waitForFunction(() => {
    return Array.from(document.querySelectorAll('#documentList li')).some((item) => {
      const text = item.textContent || '';
      return text.includes('README.md') && text.includes('可用');
    });
  }, undefined, { timeout: 30000 });
  await page.click('#railFilesBtn');
  await page.fill('#messageInput', 'capture this request');
  await page.locator('#messageInput').press('Enter');
  await page.waitForTimeout(2000);

  console.log(JSON.stringify({ askStatus, askRequestBody, askResponseBody }, null, 2));
  await browser.close();
})();
