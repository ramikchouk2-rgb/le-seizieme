import { test, expect } from '@playwright/test';
import { loginAsStaff, loginAsAdmin, createTestEvent } from './helpers';

test.describe('Negative Authorization', () => {
  test('STAFF cannot create event', async ({ page }) => {
    await loginAsStaff(page);
    await page.goto('/dashboard/events/new');
    await page.getByLabel('Nom de l\'événement *').fill('Staff Test Event');
    await page.getByLabel('Client *').fill('Staff Client');
    await page.getByLabel('Ville *').selectOption({ index: 1 });
    await page.getByLabel('Adresse *').fill('456 Staff Street');
    await page.getByLabel('Date de début *').fill('2025-12-31T20:00');
    await page.getByLabel('Date de fin *').fill('2025-12-31T23:00');
    await page.getByLabel('Nombre d\'invités *').fill('50');
    await page.getByLabel('Type d\'événement *').fill('Staff Type');
    await page.getByRole('button', { name: 'Créer l\'événement' }).click();
    const errorBox = page.locator('.bg-red-50').first();
    await expect(errorBox).toBeVisible({ timeout: 10000 });
    await expect(errorBox).toContainText(/Accès refusé|Permissions insuffisantes|erreur|error/i);
  });

  test('STAFF cannot generate staff recommendations', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await loginAsStaff(page);
    await page.goto(eventUrl);
    await page.getByRole('button', { name: 'Générer l\'équipe' }).first().click();
    const errorText = page.locator('.border-red-200 .text-red-600, .bg-red-50').first();
    await expect(errorText).toBeVisible({ timeout: 10000 });
    await expect(errorText).toContainText(/Accès refusé|Permissions insuffisantes|erreur|error/i);
  });

  test('STAFF cannot initialize attendance', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await loginAsStaff(page);
    await page.goto(`${eventUrl}/attendance`);
    await page.getByRole('button', { name: 'Initialiser les présences' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Initialiser', exact: true }).click();
    await page.waitForTimeout(2000);
    const errorText = page.locator('.bg-red-50, .border-red-200 .text-red-600, [role="alert"]').first();
    await expect(errorText).toBeVisible({ timeout: 10000 });
    await expect(errorText).toContainText(/Accès refusé|Permissions insuffisantes|erreur|error/i);
  });

  test('STAFF cannot manage requirements', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await loginAsStaff(page);
    await page.goto(eventUrl);
    await page.getByRole('button', { name: 'Ajouter un poste' }).click();
    await expect(page.getByLabel('Poste / rôle *')).toBeVisible();
    await page.getByLabel('Poste / rôle *').selectOption('Barman');
    await page.getByLabel('Nombre demandé *').fill('2');
    await page.getByRole('button', { name: 'Ajouter', exact: true }).click();
    const errorText = page.locator('.bg-red-50, .border-red-200 .text-red-600, [role="alert"]').first();
    await expect(errorText).toBeVisible({ timeout: 10000 });
    await expect(errorText).toContainText(/Accès refusé|Permissions insuffisantes|erreur|error/i);
  });

  test('STAFF cannot transport recommendation', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await loginAsStaff(page);
    await page.goto(eventUrl);
    await page.getByRole('button', { name: 'Recommander le transport' }).nth(1).click();
    const errorText = page.locator('.border-red-200 .text-red-600, .bg-red-50').first();
    await expect(errorText).toBeVisible({ timeout: 10000 });
    await expect(errorText).toContainText(/Accès refusé|Permissions insuffisantes|erreur|error/i);
  });
});