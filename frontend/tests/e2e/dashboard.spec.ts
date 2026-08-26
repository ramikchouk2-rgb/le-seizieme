import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Dashboard', () => {
  test('dashboard loads successfully', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('navigation sidebar is visible', async ({ page }) => {
    await loginAsAdmin(page);
    const sidebar = page.getByRole('complementary');
    await expect(sidebar.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: 'Serveurs' })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: 'Événements' })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: 'Gamification' })).toBeVisible();
  });

  test('user identity is displayed', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.getByRole('banner').getByText('admin@le-seizieme.local')).toBeVisible();
  });

  test('logout is accessible', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.getByRole('button', { name: 'Déconnexion' })).toBeVisible();
  });
});
