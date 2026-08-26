import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Error Path', () => {
  test('invalid event ID shows not found', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard/events/00000000-0000-0000-0000-000000000000');
    await expect(page.getByText('Événement introuvable')).toBeVisible({ timeout: 10000 });
  });

  test('attendance check-in without initialization shows error', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.goto(`${eventUrl}/attendance`);
    const checkInButton = page.getByRole('button', { name: 'Pointer entrée' });
    if (await checkInButton.count() > 0) {
      await checkInButton.first().click();
      const errorText = page.locator('.bg-red-50, .border-red-200 .text-red-600, [role="alert"]').first();
      await expect(errorText).toBeVisible({ timeout: 10000 });
      await expect(errorText).toContainText(/erreur|error|initialis/i);
    }
  });
});