# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: accessibility.spec.ts >> Accessibility >> skip navigation link exists
- Location: tests\e2e\accessibility.spec.ts:5:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.waitForURL: Test timeout of 30000ms exceeded.
=========================== logs ===========================
waiting for navigation to "/dashboard" until "load"
============================================================
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - heading "Le Seizième" [level=1] [ref=e6]
      - paragraph [ref=e7]: Connectez-vous à votre compte
    - generic [ref=e8]:
      - generic [ref=e9]: Failed to fetch
      - generic [ref=e10]:
        - generic [ref=e11]: Email
        - textbox "Email" [ref=e12]:
          - /placeholder: admin@le-seizieme.local
          - text: admin@le-seizieme.local
      - generic [ref=e13]:
        - generic [ref=e14]: Mot de passe
        - textbox "Mot de passe" [ref=e15]:
          - /placeholder: ••••••••
          - text: SecurePassword123!
      - button "Se connecter" [ref=e16] [cursor=pointer]
  - button "Open Tanstack query devtools" [ref=e67] [cursor=pointer]
  - button "Open Next.js Dev Tools" [ref=e121] [cursor=pointer]
  - alert [ref=e125]
```

# Test source

```ts
  1  | import { test, expect, type Page } from '@playwright/test';
  2  | 
  3  | const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@le-seizieme.local';
  4  | const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'SecurePassword123!';
  5  | const STAFF_EMAIL = process.env.E2E_STAFF_EMAIL || 'staff@test.com';
  6  | const STAFF_PASSWORD = process.env.E2E_STAFF_PASSWORD || 'TestPassword123!';
  7  | const API_URL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8001/api';
  8  | 
  9  | export async function loginAsAdmin(page: Page) {
  10 |   await page.goto('/login');
  11 |   await page.getByLabel('Email').fill(ADMIN_EMAIL);
  12 |   await page.getByLabel('Mot de passe').fill(ADMIN_PASSWORD);
  13 |   await page.getByRole('button', { name: 'Se connecter' }).click();
> 14 |   await page.waitForURL('/dashboard');
     |              ^ Error: page.waitForURL: Test timeout of 30000ms exceeded.
  15 | }
  16 | 
  17 | export async function loginAsStaff(page: Page) {
  18 |   await page.goto('/login');
  19 |   await page.getByLabel('Email').fill(STAFF_EMAIL);
  20 |   await page.getByLabel('Mot de passe').fill(STAFF_PASSWORD);
  21 |   await page.getByRole('button', { name: 'Se connecter' }).click();
  22 |   await page.waitForURL('/dashboard');
  23 | }
  24 | 
  25 | export async function createTestEvent(page: Page, suffix: string = ''): Promise<string> {
  26 |   const uniqueId = Date.now();
  27 |   await page.goto('/dashboard/events/new');
  28 |   await page.getByLabel('Nom de l\'événement *').fill(`E2E_TEST_${suffix}${uniqueId}`);
  29 |   await page.getByLabel('Client *').fill('E2E Test Client');
  30 |   await page.getByLabel('Ville *').selectOption({ index: 1 });
  31 |   await page.getByLabel('Adresse *').fill('123 E2E Test Street');
  32 |   await page.getByLabel('Date de début *').fill('2025-12-31T20:00');
  33 |   await page.getByLabel('Date de fin *').fill('2025-12-31T23:00');
  34 |   await page.getByLabel('Nombre d\'invités *').fill('50');
  35 |   await page.getByLabel('Type d\'événement *').fill('E2E Test Type');
  36 |   await page.getByRole('button', { name: 'Créer l\'événement' }).click();
  37 |   await page.waitForURL(/\/dashboard\/events\/[0-9a-f-]{36}$/, { timeout: 30000 });
  38 |   await expect(page.getByRole('link', { name: 'Présences' })).toBeVisible({ timeout: 30000 });
  39 |   await expect(page.getByRole('heading', { name: `E2E_TEST_${suffix}${uniqueId}` })).toBeVisible({ timeout: 30000 });
  40 |   return page.url();
  41 | }
  42 | 
  43 | export async function waitForSuccessMessage(page: Page, message: string) {
  44 |   await page.waitForSelector(`text=${message}`, { timeout: 10000 });
  45 | }
  46 | 
```