import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

async function findCompletedEventWithStaff(page: any): Promise<string> {
  await page.goto('/dashboard/events');
  
  await page.getByLabel('Statut').selectOption('COMPLETED');
  
  await page.waitForResponse((r: any) => r.url().includes('/api/events') && r.request().method() === 'GET');
  
  const firstEventLink = page.locator('table tbody tr a[href*="/dashboard/events/"]').first();
  const href = await firstEventLink.getAttribute('href');
  
  if (!href) {
    throw new Error('No COMPLETED event found in the database');
  }
  
  await firstEventLink.click();
  await expect(page.getByRole('link', { name: 'Évaluations' })).toBeVisible({ timeout: 30000 });
  
  return href;
}

test.describe('Evaluation CRUD', () => {
  test('create, edit, and delete evaluation with React Query state consistency', async ({ page }) => {
    await loginAsAdmin(page);
    const eventUrl = await findCompletedEventWithStaff(page);
    await page.goto(`${eventUrl}/evaluations`);

    while (await page.getByRole('button', { name: 'Supprimer' }).count() > 0) {
      await page.getByRole('button', { name: 'Supprimer' }).first().click();
      await expect(page.getByText('Aucune évaluation enregistrée.')).toBeVisible({ timeout: 10000 });
    }

    await page.getByRole('button', { name: '+ Nouvelle évaluation' }).click();
    await expect(page.getByLabel('Serveur *')).toBeVisible();

    const serverSelect = page.getByLabel('Serveur *');
    await serverSelect.selectOption({ index: 1 });
    const selectedOption = serverSelect.locator('option:checked');
    const serverName = (await selectedOption.textContent())?.trim() || '';
    const serverNameWithoutRole = serverName.split(' — ')[0] || serverName;

    const sliders = page.locator('input[type="range"]');
    await sliders.nth(0).fill('8');
    await sliders.nth(1).fill('7');
    await sliders.nth(2).fill('9');
    await sliders.nth(3).fill('6');
    await sliders.nth(4).fill('8');

    await page.getByLabel('Commentaire (optionnel)').fill('E2E test evaluation comment');

    const responsePromise = page.waitForResponse((r: any) => r.url().includes('/evaluations') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Enregistrer' }).click();
    const response = await responsePromise;
    expect(response.ok()).toBeTruthy();

    await expect(page.getByText(serverNameWithoutRole)).toBeVisible({ timeout: 10000 });
    const scoreText = `${((8 + 7 + 9 + 6 + 8) / 5).toFixed(1)}/10`;
    await expect(page.getByText(scoreText)).toBeVisible();
    await expect(page.getByText('E2E test evaluation comment')).toBeVisible();

    await page.getByRole('button', { name: 'Modifier' }).first().click();
    await expect(page.getByLabel('Serveur *')).toBeDisabled();

    await sliders.nth(0).fill('10');
    await sliders.nth(1).fill('9');
    await page.getByLabel('Commentaire (optionnel)').fill('Updated comment');

    const updatePromise = page.waitForResponse((r: any) => r.url().includes('/evaluations') && r.request().method() === 'PATCH');
    await page.getByRole('button', { name: 'Mettre à jour' }).click();
    const updateResponse = await updatePromise;
    expect(updateResponse.ok()).toBeTruthy();

    const updatedScoreText = `${((10 + 9 + 9 + 6 + 8) / 5).toFixed(1)}/10`;
    await expect(page.getByText(updatedScoreText)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Updated comment')).toBeVisible();

    const deletePromise = page.waitForResponse((r: any) => r.url().includes('/evaluations') && r.request().method() === 'DELETE');
    await page.getByRole('button', { name: 'Supprimer' }).first().click();
    const deleteResponse = await deletePromise;
    expect(deleteResponse.ok()).toBeTruthy();

    await expect(page.getByText('Aucune évaluation enregistrée.')).toBeVisible({ timeout: 10000 });
  });
});
