import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('UI State Consistency', () => {
  test('requirement creation updates UI immediately', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.getByRole('button', { name: 'Ajouter un poste' }).click();
    await expect(page.getByLabel('Poste / rôle *')).toBeVisible();
    await page.getByLabel('Poste / rôle *').selectOption('Barman');
    await page.getByLabel('Nombre demandé *').fill('3');
    await page.getByRole('button', { name: 'Ajouter', exact: true }).click();
    await expect(page.getByText('Poste ajouté avec succès')).toBeVisible({ timeout: 10000 });
  });

  test('attendance initialization updates UI immediately', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.goto(`${eventUrl}/attendance`);
    await page.getByRole('button', { name: 'Initialiser les présences' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Initialiser', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 10000 });
  });
});