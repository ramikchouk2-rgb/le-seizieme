import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Requirements', () => {
  test('create requirement', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.getByRole('button', { name: 'Ajouter un poste' }).click();
    await expect(page.getByLabel('Poste / rôle *')).toBeVisible();
    await page.getByLabel('Poste / rôle *').selectOption('Barman');
    await page.getByLabel('Nombre demandé *').fill('2');
    await page.getByRole('button', { name: 'Ajouter', exact: true }).click();
    await expect(page.getByText('Poste ajouté avec succès')).toBeVisible({ timeout: 10000 });
  });
});
