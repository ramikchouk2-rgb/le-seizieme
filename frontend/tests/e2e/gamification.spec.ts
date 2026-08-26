import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Gamification', () => {
  test('gamification page loads', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard/gamification');
    await expect(page.getByRole('heading', { name: 'Gamification' })).toBeVisible();
  });
});
