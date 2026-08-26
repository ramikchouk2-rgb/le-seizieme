import { test, expect } from '@playwright/test';
import { loginAsAdmin, loginAsStaff } from './helpers';

test.describe('Negative Authentication', () => {
  test('invalid credentials show French error', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill('invalid@test.com');
    await page.getByLabel('Mot de passe').fill('wrongpassword');
    await page.getByRole('button', { name: 'Se connecter' }).click();
    await expect(page.locator('.bg-red-50')).toContainText(/incorrect|non autorisé/i);
  });

  test('protected route redirects unauthenticated users to login', async ({ page }) => {
    await page.goto('/dashboard/events');
    await expect(page).toHaveURL('/login');
  });

  test('logout returns to login', async ({ page }) => {
    await loginAsAdmin(page);
    await page.getByRole('button', { name: 'Déconnexion' }).click();
    await expect(page).toHaveURL('/login');
  });

  test('cannot access dashboard after logout', async ({ page }) => {
    await loginAsAdmin(page);
    await page.getByRole('button', { name: 'Déconnexion' }).click();
    await expect(page).toHaveURL('/login');
    await page.goto('/dashboard');
    await expect(page).toHaveURL('/login');
  });
});
