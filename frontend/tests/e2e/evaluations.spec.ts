import { test, expect } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

test.describe('Evaluations', () => {
  test('evaluation form has all scoring fields', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page);
    await page.goto(`${eventUrl}/evaluations`);
    await page.getByRole('button', { name: '+ Nouvelle évaluation' }).click();
    await expect(page.getByLabel('Serveur *')).toBeVisible();
    await expect(page.getByText('Ponctualité')).toBeVisible();
    await expect(page.getByText('Qualité du travail')).toBeVisible();
    await expect(page.getByText('Présentation')).toBeVisible();
    await expect(page.getByText('Esprit d\'équipe')).toBeVisible();
    await expect(page.getByText('Relation client')).toBeVisible();
    await expect(page.getByLabel('Commentaire (optionnel)')).toBeVisible();
  });
});
