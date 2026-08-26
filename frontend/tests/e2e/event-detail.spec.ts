import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Event Detail', () => {
  test('event detail sub-navigation exists', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    expect(eventUrl).toMatch(/\/dashboard\/events\/[0-9a-f-]{36}$/);
    await expect(page.getByRole('link', { name: 'Présences' })).toBeVisible({ timeout: 60000 });
    await expect(page.getByRole('link', { name: 'Évaluations' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Opérations' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Rapport' })).toBeVisible();
  });
});
