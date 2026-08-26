import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Event Creation', () => {
  test('create event workflow', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard/events/new');
    await expect(page.getByLabel('Nom de l\'événement *')).toBeVisible();
    await page.getByLabel('Nom de l\'événement *').fill(`E2E Event ${Date.now()}`);
    await page.getByLabel('Client *').fill('E2E Client');
    await page.getByLabel('Ville *').selectOption({ index: 1 });
    await page.getByLabel('Adresse *').fill('456 E2E Street');
    await page.getByLabel('Date de début *').fill('2025-12-31T20:00');
    await page.getByLabel('Date de fin *').fill('2025-12-31T23:00');
    await page.getByLabel('Nombre d\'invités *').fill('100');
    await page.getByLabel('Type d\'événement *').fill('E2E Type');
    await page.getByRole('button', { name: 'Créer l\'événement' }).click();
    await page.waitForURL(/\/dashboard\/events\/[^/]+$/);
    await expect(page.getByRole('heading', { name: 'Événement' })).toBeVisible();
  });
});
