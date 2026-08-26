import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Staffing', () => {
  test('generate staff recommendations', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.getByRole('button', { name: 'Générer l\'équipe' }).first().click();
    await page.waitForSelector('text=Recommandations de staffing', { timeout: 30000 });
  });
});
