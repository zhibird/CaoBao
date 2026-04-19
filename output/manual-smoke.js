const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const baseUrl = 'http://127.0.0.1:8765';
  const runId = new Date().toISOString().replace(/[:.]/g, '-');
  const outDir = path.resolve('output', `manual-smoke-${runId}`);
  fs.mkdirSync(outDir, { recursive: true });

  const report = {
    baseUrl,
    outDir,
    steps: [],
    console: [],
    pageErrors: [],
    failedResponses: [],
    screenshots: [],
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();

  page.on('console', (msg) => {
    report.console.push({ type: msg.type(), text: msg.text() });
  });
  page.on('pageerror', (error) => {
    report.pageErrors.push(error.message || String(error));
  });
  page.on('response', (response) => {
    const url = response.url();
    const status = response.status();
    const expectedAuthBootstrap = /\/api\/v1\/auth\/(me|refresh)$/.test(url) && status === 401;
    const faviconMiss = url.endsWith('/favicon.ico') && status === 204;
    if (status >= 400 && !expectedAuthBootstrap && !faviconMiss) {
      report.failedResponses.push({ url, status });
    }
  });

  function assert(condition, message) {
    if (!condition) {
      throw new Error(message);
    }
  }

  async function shot(filename) {
    const target = path.join(outDir, filename);
    await page.screenshot({ path: target, fullPage: true });
    report.screenshots.push(target);
    return target;
  }

  async function waitVisible(selector, timeout = 15000) {
    await page.waitForFunction(
      (sel) => {
        const el = document.querySelector(sel);
        return !!el && !el.classList.contains('hidden');
      },
      selector,
      { timeout },
    );
  }

  async function waitHidden(selector, timeout = 15000) {
    await page.waitForFunction(
      (sel) => {
        const el = document.querySelector(sel);
        return !!el && el.classList.contains('hidden');
      },
      selector,
      { timeout },
    );
  }

  async function step(name, fn) {
    try {
      const details = await fn();
      report.steps.push({ name, status: 'passed', details: details || null });
    } catch (error) {
      report.steps.push({ name, status: 'failed', error: error.stack || String(error) });
      throw error;
    }
  }

  try {
    await page.goto(baseUrl, { waitUntil: 'networkidle' });

    await step('1. launch panel appears before first message', async () => {
      assert(await page.locator('#heroPanel').isVisible(), 'heroPanel is not visible on initial load');
      assert((await page.locator('#messageList .message').count()) === 0, 'message list is not empty before first send');
      const screenshot = await shot('01-initial-desktop.png');
      return { screenshot };
    });

    const userId = `smoke_${Date.now()}`;
    const password = 'smoketest123';

    await step('auth bootstrap via register modal', async () => {
      const authAlreadyVisible = await page.locator('#authModal').isVisible();
      if (!authAlreadyVisible) {
        await page.click('#railSettingsBtn');
        await waitVisible('#authModal');
      }
      await page.click('#authRegisterTab');
      await page.fill('#registerUserIdInput', userId);
      await page.fill('#registerDisplayNameInput', 'Smoke User');
      await page.fill('#registerPasswordInput', password);
      await page.fill('#registerConfirmPasswordInput', password);
      await Promise.all([
        page.waitForResponse((response) => response.url().includes('/api/v1/auth/register') && response.status() === 201),
        page.click('#registerAuthBtn'),
      ]);
      await waitHidden('#authModal');
      await page.waitForFunction(
        () => {
          const name = document.querySelector('#profileName');
          return !!name && name.textContent && !name.textContent.includes('未进入工作台');
        },
        undefined,
        { timeout: 15000 },
      );
      return { userId };
    });

    await step('2. rail new chat returns focus to composer', async () => {
      await page.click('#railNewChatBtn');
      await page.waitForFunction(
        () => document.activeElement && document.activeElement.id === 'messageInput',
        undefined,
        { timeout: 15000 },
      );
      const conversationCount = await page.locator('#historyList li').count();
      assert(conversationCount >= 1, 'no conversation item rendered after creating a new chat');
      return { conversationCount };
    });

    await step('3. conversations drawer opens and Escape closes it', async () => {
      await page.click('#railConversationsBtn');
      await waitVisible('#conversationDrawer');
      const screenshot = await shot('03-conversations-drawer.png');
      await page.keyboard.press('Escape');
      await waitHidden('#conversationDrawer');
      return { screenshot };
    });

    await step('4. files drawer previews an uploaded file', async () => {
      await page.click('#toggleImportBtn');
      await waitVisible('#attachMenu');
      const [chooser] = await Promise.all([
        page.waitForEvent('filechooser'),
        page.click('#uploadFileBtn'),
      ]);
      await chooser.setFiles(path.resolve('README.md'));

      await page.click('#railFilesBtn');
      await waitVisible('#fileDrawer');
      await page.waitForFunction(
        () => {
          return Array.from(document.querySelectorAll('#documentList li')).some((item) => {
            const text = item.textContent || '';
            return text.includes('README.md') && text.includes('可用');
          });
        },
        undefined,
        { timeout: 30000 },
      );

      const titleButton = page.locator('#documentList .doc-card-action', { hasText: 'README.md' }).first();
      await titleButton.click();
      await waitVisible('#previewDrawer');
      const previewTitle = await page.locator('#previewTitle').textContent();
      const screenshot = await shot('04-file-preview.png');
      await page.click('#closePreviewBtn');
      await waitHidden('#previewDrawer');
      await page.click('#railFilesBtn');
      await waitHidden('#fileDrawer');
      return { previewTitle, screenshot };
    });

    await step('5. first message switches into chat stage', async () => {
      await page.locator('#messageInput').click();
      await page.fill('#messageInput', '你好，做个 smoke test。');
      await page.locator('#messageInput').press('Enter');
      await page.waitForFunction(
        () => document.querySelectorAll('#messageList .message').length >= 2,
        undefined,
        { timeout: 30000 },
      );
      await page.waitForFunction(
        () => document.querySelector('#heroPanel')?.classList.contains('hidden'),
        undefined,
        { timeout: 15000 },
      );
      await page.waitForFunction(
        () => document.querySelector('.shell')?.classList.contains('workspace-stage-chat'),
        undefined,
        { timeout: 15000 },
      );
      const focusedElement = await page.evaluate(() => document.activeElement && document.activeElement.id);
      const screenshot = await shot('05-chat-stage.png');
      return { focusedElement, screenshot };
    });

    await step('6. settings and auth surfaces still open from rail', async () => {
      await page.click('#railSettingsBtn');
      await waitVisible('#settingsModal');
      assert(await page.locator('#switchAccountBtn').isVisible(), 'settings modal did not show account actions');
      const screenshot = await shot('06-settings-modal.png');
      await page.click('#switchAccountBtn');
      await waitVisible('#authModal');
      assert(await page.locator('#authLoginTab').isVisible(), 'auth modal did not open from settings');
      await page.click('#cancelAuthBtn');
      await waitHidden('#authModal');
      return { screenshot };
    });

    await step('7. favorites view and back keeps shell intact', async () => {
      await page.click('#favoritesWorkspaceBtn');
      await page.waitForFunction(
        () => !document.querySelector('#favoritesPanel')?.classList.contains('hidden'),
        undefined,
        { timeout: 15000 },
      );
      await page.click('#chatWorkspaceBtn');
      await page.waitForFunction(
        () => document.querySelector('#favoritesPanel')?.classList.contains('hidden'),
        undefined,
        { timeout: 15000 },
      );
      assert(await page.locator('#messageInput').isVisible(), 'composer disappeared after returning from favorites');
      assert(await page.locator('#workspaceRail').isVisible(), 'workspace rail disappeared after returning from favorites');
      const favoritesLabel = await page.locator('#favoritesWorkspaceBtn').textContent();
      return { favoritesLabel };
    });

    await step('8. narrow viewport uses overlay-style recall surfaces', async () => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForTimeout(400);
      const railStyles = await page.$eval('#workspaceRail', (el) => {
        const styles = getComputedStyle(el);
        return {
          display: styles.display,
          flexDirection: styles.flexDirection,
        };
      });
      assert(railStyles.display !== 'none', 'workspace rail is hidden on narrow viewport');
      assert(railStyles.flexDirection === 'row', 'workspace rail did not collapse into a horizontal mobile bar');

      await page.click('#railConversationsBtn');
      await waitVisible('#conversationDrawer');
      const drawerStyles = await page.$eval('#conversationDrawer', (el) => {
        const styles = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return {
          position: styles.position,
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
        };
      });
      assert(drawerStyles.position === 'absolute', 'conversation drawer is not rendered as an overlay surface on mobile');
      const screenshot = await shot('08-mobile-overlay.png');
      await page.keyboard.press('Escape');
      await waitHidden('#conversationDrawer');
      return { railStyles, drawerStyles, screenshot };
    });

    const seriousConsole = report.console.filter((item) => {
      if (item.type !== 'error') {
        return false;
      }
      return !/401/.test(item.text);
    });

    report.summary = {
      seriousConsoleCount: seriousConsole.length,
      pageErrorCount: report.pageErrors.length,
      failedResponseCount: report.failedResponses.length,
      stepCount: report.steps.length,
    };

    if (seriousConsole.length || report.pageErrors.length || report.failedResponses.length) {
      throw new Error(`Unexpected browser issues: console=${seriousConsole.length}, pageErrors=${report.pageErrors.length}, failedResponses=${report.failedResponses.length}`);
    }

    fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify({ outDir, summary: report.summary, steps: report.steps }, null, 2));
    await browser.close();
  } catch (error) {
    fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 2));
    await browser.close();
    throw error;
  }
})();
