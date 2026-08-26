import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Urgent Staffing', () => {
  test('urgent staffing panel visible on urgent event', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard/events/new');
    await page.getByLabel('Nom de l\'événement *').fill(`Urgent Event ${Date.now()}`);
    await page.getByLabel('Client *').fill('Urgent Client');
    await page.getByLabel('Ville *').selectOption({ index: 1 });
    await page.getByLabel('Adresse *').fill('123 Urgent Street');
    await page.getByLabel('Date de début *').fill('2025-12-31T20:00');
    await page.getByLabel('Date de fin *').fill('2025-12-31T23:00');
    await page.getByLabel('Nombre d\'invités *').fill('50');
    await page.getByLabel('Type d\'événement *').fill('Urgent Type');
    await page.getByLabel('Priorité').selectOption('URGENT');
    await page.getByRole('button', { name: 'Créer l\'événement' }).click();
    await page.waitForURL(/\/dashboard\/events\/[0-9a-f-]{36}$/, { timeout: 30000 });
    await page.reload();
    await expect(page.getByText('Staffing urgent')).toBeVisible({ timeout: 30000 });
  });
});
