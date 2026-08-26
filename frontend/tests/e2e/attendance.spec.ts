import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Attendance', () => {
  test('initialize attendance', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.goto(`${eventUrl}/attendance`);
    await page.getByRole('button', { name: 'Initialiser les présences' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Initialiser', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 10000 });
  });
});
