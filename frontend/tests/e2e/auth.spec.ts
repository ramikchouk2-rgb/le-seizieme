import { test, expect, type Page } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('login form is visible', async ({ page }) => {
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Mot de passe')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible();
  });

  test('invalid credentials show French error', async ({ page }) => {
    await page.getByLabel('Email').fill('invalid@test.com');
    await page.getByLabel('Mot de passe').fill('wrongpassword');
    await page.getByRole('button', { name: 'Se connecter' }).click();

    await expect(page.locator('.bg-red-50')).toContainText(/incorrect|erreur|non autorisé/i);
  });

  test('valid credentials enter dashboard', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page).toHaveURL('/dashboard');
  });

  test('authenticated user identity is displayed', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.getByRole('banner').getByText('admin@le-seizieme.local')).toBeVisible();
  });

  test('logout returns to /login', async ({ page }) => {
    await loginAsAdmin(page);
    await page.getByRole('button', { name: 'Déconnexion' }).click();
    await expect(page).toHaveURL('/login');
  });

  test('protected route redirects unauthenticated users', async ({ page }) => {
    await page.goto('/dashboard/events');
    await expect(page).toHaveURL('/login');
  });
});
