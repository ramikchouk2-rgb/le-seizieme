import { test, expect } from '@playwright/test';
import { loginAsStaff } from './helpers';

test.describe('Gamification Authorization', () => {
  test('STAFF cannot award completion points', async ({ page }) => {
    await loginAsStaff(page);
    await page.goto('/dashboard/gamification');
    const awardButton = page.getByRole('button', { name: 'Attribuer les points de présence' });
    if (await awardButton.count() > 0) {
      await awardButton.first().click();
      const errorText = page.locator('.bg-red-50, .border-red-200 .text-red-600, [role="alert"]').first();
      await expect(errorText).toBeVisible({ timeout: 10000 });
      await expect(errorText).toContainText(/Accès refusé|Permissions insuffisantes|erreur|error/i);
    }
  });
});