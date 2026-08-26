import { test, expect, type Page } from '@playwright/test';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@le-seizieme.local';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'SecurePassword123!';
const STAFF_EMAIL = process.env.E2E_STAFF_EMAIL || 'staff@test.com';
const STAFF_PASSWORD = process.env.E2E_STAFF_PASSWORD || 'TestPassword123!';
const API_URL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8001/api';

export async function loginAsAdmin(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(ADMIN_EMAIL);
  await page.getByLabel('Mot de passe').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await page.waitForURL('/dashboard');
}

export async function loginAsStaff(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(STAFF_EMAIL);
  await page.getByLabel('Mot de passe').fill(STAFF_PASSWORD);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await page.waitForURL('/dashboard');
}

export async function createTestEvent(page: Page, suffix: string = ''): Promise<string> {
  const uniqueId = Date.now();
  await page.goto('/dashboard/events/new');
  await page.getByLabel('Nom de l\'événement *').fill(`E2E_TEST_${suffix}${uniqueId}`);
  await page.getByLabel('Client *').fill('E2E Test Client');
  await page.getByLabel('Ville *').selectOption({ index: 1 });
  await page.getByLabel('Adresse *').fill('123 E2E Test Street');
  await page.getByLabel('Date de début *').fill('2025-12-31T20:00');
  await page.getByLabel('Date de fin *').fill('2025-12-31T23:00');
  await page.getByLabel('Nombre d\'invités *').fill('50');
  await page.getByLabel('Type d\'événement *').fill('E2E Test Type');
  await page.getByRole('button', { name: 'Créer l\'événement' }).click();
  await page.waitForURL(/\/dashboard\/events\/[0-9a-f-]{36}$/, { timeout: 30000 });
  await expect(page.getByRole('link', { name: 'Présences' })).toBeVisible({ timeout: 30000 });
  await expect(page.getByRole('heading', { name: `E2E_TEST_${suffix}${uniqueId}` })).toBeVisible({ timeout: 30000 });
  return page.url();
}

export async function waitForSuccessMessage(page: Page, message: string) {
  await page.waitForSelector(`text=${message}`, { timeout: 10000 });
}
