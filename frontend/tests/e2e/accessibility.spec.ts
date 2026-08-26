import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Accessibility', () => {
  test('skip navigation link exists', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard');
    const skipLink = page.getByRole('link', { name: 'Passer au contenu principal' });
    await expect(skipLink).toBeVisible();
  });

  test('dialog has role aria-modal and aria-labelledby', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.getByRole('button', { name: 'Ajouter un poste' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('aria-modal', 'true');
    await expect(dialog).toHaveAttribute('aria-labelledby');
  });

  test('form inputs have associated labels', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard/events/new');
    await expect(page.getByLabel('Nom de l\'événement *')).toBeVisible();
    await expect(page.getByLabel('Client *')).toBeVisible();
    await expect(page.getByLabel('Ville *')).toBeVisible();
    await expect(page.getByLabel('Adresse *')).toBeVisible();
    await expect(page.getByLabel('Date de début *')).toBeVisible();
    await expect(page.getByLabel('Date de fin *')).toBeVisible();
    await expect(page.getByLabel('Nombre d\'invités *')).toBeVisible();
    await expect(page.getByLabel('Type d\'événement *')).toBeVisible();
  });

  test('tables have scope attributes', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard/servers');
    const tableHeaders = page.locator('th[scope="col"]');
    await expect(tableHeaders.first()).toBeVisible();
  });

  test('aria-live region exists for announcements', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard');
    const liveRegion = page.locator('[aria-live="polite"], [aria-live="assertive"]');
    await expect(liveRegion.first()).toBeVisible();
  });

  test('dialog close button has accessible name', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.getByRole('button', { name: 'Ajouter un poste' }).click();
    await expect(page.getByRole('button', { name: 'Fermer' })).toBeVisible();
  });

  test('Escape closes dialog', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.getByRole('button', { name: 'Ajouter un poste' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });
});