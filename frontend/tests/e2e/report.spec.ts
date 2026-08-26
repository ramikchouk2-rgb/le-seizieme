import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Event Report', () => {
  test('event report loads', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.goto(`${eventUrl}/report`);
    await expect(page.getByRole('heading', { name: 'Rapport final' })).toBeVisible({ timeout: 60000 });
  });
});
