import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Transport', () => {
  test('generate transport recommendation', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.getByRole('button', { name: 'Recommander le transport' }).nth(1).click();
    await page.waitForSelector('text=Transport recommandé', { timeout: 30000 });
  });
});
