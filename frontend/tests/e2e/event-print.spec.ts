import { test, expect, type Page } from '@playwright/test';
import { loginAsAdmin, createTestEvent } from './helpers';

/**
 * Step 24C-D-10: the printable operational sheet.
 *
 * Two kinds of test live here on purpose:
 *
 * 1. REAL-BACKEND tests. The page must load and read exactly one endpoint:
 *    `GET /api/events/{event_id}/print-data`. These prove the route, the auth
 *    boundary and the request shape against the live API.
 *
 * 2. FIXTURE tests via `page.route`. Rendering and privacy are asserted against
 *    a controlled payload, because that is the only way to prove a negative:
 *    a fixture can contain venue coordinates and a PENDING/REJECTED
 *    attestation, so we can show they are never rendered. A live event with
 *    clean data proves nothing about that.
 */

const PRINT_PATH = '/print';

/**
 * Fixture shape.
 *
 * Explicit rather than inferred so a test can legitimately assign `null` to an
 * optional field (`verified_at`, `uniform_size`) — which is exactly the case the
 * placeholder assertions depend on.
 */
interface AttestationFixture {
  attestation_id: string;
  qualification_name: string;
  status: string;
  verified_at: string | null;
}

interface AssignmentFixture extends Record<string, unknown> {
  server_id: string;
  uniform_size: string | null;
  profile_photo_available: boolean;
  actual_skills: Array<Record<string, unknown>>;
  verified_attestations: AttestationFixture[];
}

interface TransportGroupFixture extends Record<string, unknown> {
  status: string;
}

interface PrintFixture {
  event: Record<string, unknown> & { latitude: number; longitude: number };
  requirements: Array<Record<string, unknown>>;
  assignments: AssignmentFixture[];
  transport_groups: TransportGroupFixture[];
}

/** A minimal but complete print-data payload. */
function makePrintData(overrides: Partial<PrintFixture> = {}): PrintFixture {
  return {
    event: {
      id: '11111111-1111-1111-1111-111111111111',
      name: 'E2E_PRINT_EVENT',
      client_name: 'E2E Client',
      event_type: 'PRIVATE',
      start_datetime: '2030-05-04T20:00:00',
      end_datetime: '2030-05-04T23:30:00',
      city: 'Tunis',
      address: '1 Rue de la Fiche',
      // Venue coordinates. INTERNAL: the sheet must never show these.
      latitude: 36.8078,
      longitude: 10.181,
      guest_count: 120,
      status: 'CONFIRMED',
      priority: 'HIGH',
      urgent: false,
      required_response_minutes: 45,
      notes: 'Prévoir deux glacières.',
      has_exact_location: true,
    },
    requirements: [
      {
        requirement_id: 'aaaa1111-1111-1111-1111-111111111111',
        role_name: 'Serveur',
        quantity: 3,
        required_gender: 'MALE',
        minimum_experience: 2,
        required_minimum_skill_level: 4,
        selected: 1,
        missing: 2,
      },
    ],
    assignments: [
      {
        server_id: 'bbbb2222-2222-2222-2222-222222222222',
        first_name: 'Amine',
        last_name: 'Ben Salah',
        gender: 'MALE',
        city: 'Tunis',
        years_experience: 5,
        role: 'Serveur',
        assignment_status: 'CONFIRMED',
        assigned_at: '2030-04-01T10:00:00',
        confirmed_at: '2030-04-01T11:00:00',
        required_minimum_skill_level: 4,
        score: null,
        uniform_size: 'L',
        profile_photo_available: false,
        actual_skills: [
          { skill_id: 'cccc3333-3333-3333-3333-333333333333', skill_name: 'Service', level: 9, years_experience: 4 },
        ],
        verified_attestations: [
          {
            attestation_id: 'dddd4444-4444-4444-4444-444444444444',
            qualification_name: 'Hygiène et sécurité',
            status: 'VERIFIED',
            verified_at: '2030-03-01T09:00:00',
          },
        ],
      },
    ],
    transport_groups: [
      {
        transport_group_id: 'eeee5555-5555-5555-5555-555555555555',
        driver_server_id: 'ffff6666-6666-6666-6666-666666666666',
        driver_name: 'Karim Trabelsi',
        vehicle: 'Renault Clio',
        vehicle_type: 'HATCHBACK',
        capacity: 5,
        passenger_count: 2,
        departure_time: '2030-05-04T18:30:00',
        departure_location_label: 'Siège social',
        destination_label: 'Hôtel La Résidence',
        estimated_duration_minutes: 25,
        estimated_distance_km: 8.5,
        estimated_route_distance_km: 9.12,
        has_exact_location: true,
        status: 'CONFIRMED',
        passengers: [
          {
            server_id: 'bbbb2222-2222-2222-2222-222222222222',
            name: 'Amine Ben Salah',
            pickup_order: 1,
            pickup_status: 'PENDING',
            pickup_location_label: 'Café El Marsa',
          },
        ],
      },
    ],
    ...overrides,
  };
}

/**
 * Serve a controlled print-data payload and record how the page called the API.
 *
 * `calls` is asserted directly, so "the page reads exactly this one endpoint"
 * is verified rather than assumed.
 */
async function stubPrintData(page: Page, payload: unknown, options: { stubPhoto?: boolean } = {}) {
  const calls: { url: string; method: string }[] = [];
  await page.route('**/api/events/*/print-data', async (route) => {
    calls.push({ url: route.request().url(), method: route.request().method() });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    });
  });
  // Block the per-server photo endpoint: several tests assert the placeholder.
  // Playwright resolves the most recently registered matching route first, so
  // tests that serve a real photo must opt out rather than register their own
  // route and be shadowed by this one.
  if (options.stubPhoto !== false) {
    await page.route('**/api/servers/*/files/profile-photo', (route) =>
      route.fulfill({ status: 404, contentType: 'application/json', body: '{}' })
    );
  }
  return calls;
}

/**
 * Record window.print() calls.
 *
 * Headless Chromium treats print() as a no-op, so it is replaced with a counter.
 * This is how we prove print is triggered by the print workflow and NOT by the
 * event detail page.
 */
async function trackPrintCalls(page: Page) {
  await page.addInitScript(() => {
    (window as unknown as { __printCalls: number }).__printCalls = 0;
    window.print = () => {
      (window as unknown as { __printCalls: number }).__printCalls += 1;
    };
  });
  return async () =>
    page.evaluate(() => (window as unknown as { __printCalls: number }).__printCalls);
}

const EVENT_ID = '11111111-1111-1111-1111-111111111111';
const PRINT_URL = `/dashboard/events/${EVENT_ID}${PRINT_PATH}`;

/* ===================================================== real backend tests */

test.describe('Print sheet — live endpoint', () => {
  test('reads exactly the print-data endpoint and renders the event name', async ({ page }) => {
    const requested: string[] = [];
    page.on('request', (r) => {
      if (r.url().includes('/print-data')) requested.push(`${r.method()} ${new URL(r.url()).pathname}`);
    });

    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page, 'print');
    const eventId = new URL(eventUrl).pathname.split('/').pop() as string;

    await page.goto(`${eventUrl}${PRINT_PATH}`);

    // (B) loads, and (C) event information is rendered.
    await expect(page.getByTestId('print-event-name')).toBeVisible({ timeout: 60000 });
    await expect(page.getByTestId('print-event-name')).toContainText('E2E_TEST_print');

    // (A) exactly one call, to GET /api/events/{id}/print-data, nothing else.
    expect(requested).toEqual([`GET /api/events/${eventId}/print-data`]);

    // The sheet must not depend on the event-detail payload.
    const detailCalls: string[] = [];
    page.on('request', (r) => {
      const p = new URL(r.url()).pathname;
      if (p === `/api/events/${eventId}`) detailCalls.push(p);
    });
    await page.reload();
    await expect(page.getByTestId('print-event-name')).toBeVisible({ timeout: 60000 });
    expect(detailCalls, 'print page must not load the event-detail endpoint').toEqual([]);
  });

  test('an unknown event shows the error state, not a blank sheet', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/dashboard/events/00000000-0000-0000-0000-000000000000/print');
    // Either a retryable error card or a hard error; in both cases there must
    // be no printable sheet.
    await expect(page.getByTestId('print-event-name')).toHaveCount(0, { timeout: 60000 });
    await expect(page.getByRole('link', { name: /Retour/ }).first()).toBeVisible({ timeout: 60000 });
  });

  test('unauthenticated access is redirected away', async ({ page }) => {
    await page.goto(PRINT_URL);
    await expect(page).not.toHaveURL(new RegExp(`${PRINT_PATH}$`), { timeout: 30000 });
  });
});

/* ======================================================= fixture: content */

test.describe('Print sheet — rendered content', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('renders event, venue, requirements, staff and transport', async ({ page }) => {
    await stubPrintData(page, makePrintData());
    await page.goto(PRINT_URL);

    await expect(page.getByTestId('print-event-name')).toBeVisible();

    // Header / event identity.
    const sheetHeader = page.locator('.print-sheet-header');
    await expect(sheetHeader.getByText('LE SEIZIÈME')).toBeVisible();
    await expect(sheetHeader.getByText('Fiche opérationnelle — Événement')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Informations' })).toBeVisible();
    await expect(page.getByText('120')).toBeVisible();

    // (D) requirements.
    const reqTable = page.getByTestId('print-requirements');
    await expect(reqTable).toBeVisible();
    await expect(reqTable.getByRole('cell', { name: 'Serveur' })).toBeVisible();
    await expect(page.getByTestId('print-requirement-minimum')).toHaveText('4');

    // (E) assigned servers + (F) uniform size.
    const cards = page.getByTestId('print-staff-card');
    await expect(cards).toHaveCount(1);
    await expect(cards.getByText('Amine')).toBeVisible();
    await expect(cards.getByText('Ben Salah')).toBeVisible();
    await expect(page.getByTestId('print-uniform-size')).toContainText('L');

    // (I) transport.
    await expect(page.getByRole('heading', { name: 'Transport & logistique' })).toBeVisible();
    await expect(page.getByText('Karim Trabelsi')).toBeVisible();
    await expect(page.getByText('Renault Clio')).toBeVisible();
    await expect(page.getByText(/Café El Marsa/)).toBeVisible();
    await expect(page.getByText(/Hôtel La Résidence/)).toBeVisible();
    await expect(page.getByText(/Passagers \(1\) — hors chauffeur/)).toBeVisible();

    // Notes, because the contract actually returned one.
    await expect(page.getByRole('heading', { name: 'Notes opérationnelles' })).toBeVisible();
    await expect(page.getByText('Prévoir deux glacières.')).toBeVisible();
  });

  test('actual skills are rendered separately from the requirement minimum', async ({ page }) => {
    await stubPrintData(page, makePrintData());
    await page.goto(PRINT_URL);

    // (G) Two distinct figures, explicitly labelled.
    await expect(page.getByTestId('print-assignment-minimum')).toHaveText('4');
    const actual = page.getByTestId('print-actual-skills');
    await expect(actual).toBeVisible();
    await expect(actual.getByText('Service')).toBeVisible();
    await expect(actual.getByText(/Niveau 9/)).toBeVisible();

    // The real level must never be labelled as the requirement minimum.
    await expect(page.getByTestId('print-assignment-minimum')).not.toHaveText('9');
    // The required-minimum block is explicitly marked as a threshold.
    await expect(page.getByText('Seuil de l\'exigence, pas le niveau du serveur.')).toBeVisible();
  });

  test('verified qualifications render, and only when VERIFIED', async ({ page }) => {
    // The backend filters, but the UI must not trust that blindly: a payload
    // carrying PENDING and REJECTED rows must not print them as qualifications.
    const payload = makePrintData();
    payload.assignments[0].verified_attestations = [
      { attestation_id: 'x1', qualification_name: 'QUALIF_VERIFIEE', status: 'VERIFIED', verified_at: '2030-03-01T09:00:00' },
      { attestation_id: 'x2', qualification_name: 'QUALIF_EN_ATTENTE', status: 'PENDING', verified_at: null },
      { attestation_id: 'x3', qualification_name: 'QUALIF_REFUSEE', status: 'REJECTED', verified_at: null },
    ];

    await stubPrintData(page, payload);
    await page.goto(PRINT_URL);

    // (H) only the verified one is present.
    await expect(page.getByText('QUALIF_VERIFIEE')).toBeVisible();
    await expect(page.getByText('QUALIF_EN_ATTENTE')).toHaveCount(0);
    await expect(page.getByText('QUALIF_REFUSEE')).toHaveCount(0);
  });

  test('missing photo gets a neutral placeholder, never a broken image', async ({ page }) => {
    await stubPrintData(page, makePrintData());
    await page.goto(PRINT_URL);

    // (J) profile_photo_available is false, so no photo is requested and the
    // placeholder shows.
    await expect(page.getByTestId('print-photo-placeholder')).toBeVisible();
    await expect(page.getByText('Photo non disponible')).toBeVisible();
    await expect(page.getByTestId('print-photo-image')).toHaveCount(0);
  });

  test('a declared photo is fetched from the authenticated endpoint', async ({ page }) => {
    const requested: string[] = [];
    await page.route('**/api/servers/*/files/profile-photo', async (route) => {
      requested.push(new URL(route.request().url()).pathname);
      // 1x1 transparent PNG.
      await route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
          'base64'
        ),
      });
    });

    const payload = makePrintData();
    payload.assignments[0].profile_photo_available = true;
    await stubPrintData(page, payload, { stubPhoto: false });

    await page.goto(PRINT_URL);
    await expect(page.getByTestId('print-photo-image')).toBeVisible({ timeout: 30000 });

    // No invented public URL: the bytes come from the authenticated endpoint, and
    // from nowhere else. React StrictMode double-invokes effects in dev, so the
    // count is not asserted; the set of distinct URLs is.
    const PHOTO_PATH =
      '/api/servers/bbbb2222-2222-2222-2222-222222222222/files/profile-photo';
    expect([...new Set(requested)]).toEqual([PHOTO_PATH]);
    expect(requested.length).toBeGreaterThan(0);
    for (const path of requested) {
      expect(path).toMatch(/^\/api\/servers\/[0-9a-f-]{36}\/files\/profile-photo$/);
    }
    // And the sheet contains no storage path or file id.
    const html = await page.content();
    expect(html).not.toContain('/uploads/');
  });

  test('empty states: no qualifications, no transport, no requirements', async ({ page }) => {
    const payload = makePrintData();
    payload.assignments[0].verified_attestations = [];
    payload.assignments[0].actual_skills = [];
    payload.transport_groups = [];
    payload.requirements = [];

    await stubPrintData(page, payload);
    await page.goto(PRINT_URL);

    // (K) empty states.
    await expect(page.getByTestId('print-no-attestation')).toHaveText('Aucune qualification vérifiée');
    await expect(page.getByTestId('print-no-actual-skills')).toBeVisible();
    await expect(page.getByText('Aucun transport confirmé.')).toBeVisible();
    await expect(page.getByText('Aucun besoin en personnel défini.')).toBeVisible();
  });

  test('a cancelled transport group is not presented as active transport', async ({ page }) => {
    const payload = makePrintData();
    payload.transport_groups[0].status = 'CANCELLED';
    await stubPrintData(page, payload);
    await page.goto(PRINT_URL);

    // The backend excludes cancelled groups, but a payload carrying one must
    // not print it as confirmed transport.
    await expect(page.getByText('Aucun transport confirmé.')).toBeVisible();
    await expect(page.getByText('Karim Trabelsi')).toHaveCount(0);
  });

  test('an unknown uniform size renders the null placeholder', async ({ page }) => {
    const payload = makePrintData();
    payload.assignments[0].uniform_size = null;
    await stubPrintData(page, payload);
    await page.goto(PRINT_URL);

    await expect(page.getByTestId('print-uniform-size')).toContainText('Non renseignée');
  });
});

/* ======================================================== fixture: privacy */

test.describe('Print sheet — privacy', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('venue coordinates are never rendered', async ({ page }) => {
    const payload = makePrintData();
    // Distinctive values: if either appears in the document, it leaked.
    payload.event.latitude = 36.123456;
    payload.event.longitude = 10.987654;
    await stubPrintData(page, payload);
    await page.goto(PRINT_URL);
    await expect(page.getByTestId('print-event-name')).toBeVisible();

    const text = await page.locator('body').innerText();
    // (L) no coordinates anywhere in the rendered sheet.
    expect(text).not.toContain('36.123456');
    expect(text).not.toContain('10.987654');
    // Venue is shown by address and city instead.
    await expect(page.getByText('1 Rue de la Fiche')).toBeVisible();
    await expect(page.getByText('Tunis').first()).toBeVisible();
  });

  test('no server GPS, storage path, file id, token or internal id is rendered', async ({ page }) => {
    const payload = makePrintData();
    payload.assignments[0].server_id = 'server-gps-9f8e7d';
    payload.assignments[0].verified_attestations[0].attestation_id = 'att-internal-1234';
    await stubPrintData(page, payload);
    await page.goto(PRINT_URL);
    await expect(page.getByTestId('print-event-name')).toBeVisible();

    const text = await page.locator('body').innerText();
    for (const forbidden of [
      'server-gps-9f8e7d',       // internal server id
      'att-internal-1234',      // internal attestation id
      'uploads/',
      'storage',
      'Bearer ',
      'password',
      'latitude',
      'longitude',
    ]) {
      expect(text.toLowerCase(), `print sheet leaked "${forbidden}"`).not.toContain(
        forbidden.toLowerCase()
      );
    }
  });

  test('the sheet exposes no raw coordinate pair even in the DOM', async ({ page }) => {
    await stubPrintData(page, makePrintData());
    await page.goto(PRINT_URL);
    await expect(page.getByTestId('print-event-name')).toBeVisible();

    // Coordinates could leak through an attribute or a hidden node, so the
    // whole serialised document is checked, not just the visible text.
    const html = await page.content();
    expect(html).not.toContain('36.8078');
    expect(html).not.toContain('10.1810');
  });
});

/* ==================================================== fixture: print trigger */

test.describe('Print sheet — print trigger', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('window.print() is called on the print page once data has loaded', async ({ page }) => {
    const getPrintCalls = await trackPrintCalls(page);
    await stubPrintData(page, makePrintData());

    await page.goto(PRINT_URL);
    // Wait for the sheet, then for the auto-print that follows it.
    await expect(page.getByTestId('print-event-name')).toBeVisible();
    await expect.poll(getPrintCalls, { timeout: 15000 }).toBeGreaterThan(0);
    expect(await getPrintCalls()).toBe(1);
  });

  test('nothing is printed while the data is still loading', async ({ page }) => {
    const getPrintCalls = await trackPrintCalls(page);
    // Hold the response open so the sheet cannot render yet.
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route('**/api/events/*/print-data', async (route) => {
      await gate;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(makePrintData()),
      });
    });

    await page.goto(PRINT_URL);
    await expect(page.getByText(/Préparation de la fiche/)).toBeVisible({ timeout: 30000 });
    // (M) the loading state must not have triggered a print.
    await page.waitForTimeout(1500);
    expect(await getPrintCalls()).toBe(0);

    release();
    await expect(page.getByTestId('print-event-name')).toBeVisible({ timeout: 30000 });
    await expect.poll(getPrintCalls, { timeout: 15000 }).toBeGreaterThan(0);
  });

  test('window.print() is NOT called by the event detail page', async ({ page }) => {
    const getPrintCalls = await trackPrintCalls(page);
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page, 'noprint');

    // The detail page offers a link to the sheet, but must never print itself.
    await expect(page.getByTestId('event-print-link')).toBeVisible({ timeout: 60000 });
    await page.waitForTimeout(1200);
    expect(await getPrintCalls()).toBe(0);
    await page.goto(`${eventUrl}#`);
  });

  test('the detail page links to the print page and does not print in place', async ({ page }) => {
    const getPrintCalls = await trackPrintCalls(page);
    await loginAsAdmin(page);
    const eventUrl = await createTestEvent(page, 'nav');

    const link = page.getByTestId('event-print-link');
    await expect(link).toBeVisible({ timeout: 60000 });
    expect(await getPrintCalls()).toBe(0);

    // Clicking navigates; the print happens on the destination page.
    await link.click();
    await expect(page).toHaveURL(/\/print$/, { timeout: 30000 });
    await expect(page.getByTestId('print-event-name')).toBeVisible({ timeout: 60000 });
    await expect.poll(getPrintCalls, { timeout: 15000 }).toBeGreaterThan(0);
  });
});

/* ==================================================== fixture: print styles */

test.describe('Print sheet — print stylesheet', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('(N) the toolbar is hidden under @media print but the sheet is not', async ({ page }) => {
    await stubPrintData(page, makePrintData());
    await page.goto(PRINT_URL);
    await expect(page.getByTestId('print-event-name')).toBeVisible();

    // On screen the controls exist.
    await expect(page.getByRole('button', { name: 'Imprimer' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Retour' })).toBeVisible();

    // Under print media they must be gone, while the document remains.
    await page.emulateMedia({ media: 'print' });
    await expect(page.getByRole('button', { name: 'Imprimer' })).toBeHidden();
    await expect(page.getByTestId('print-event-name')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Besoins en personnel' })).toBeVisible();

    // The dashboard chrome is removed too.
    await expect(page.locator('aside')).toBeHidden();
    await expect(page.locator('header').first()).toBeHidden();
  });

  test('the page does not require horizontal scrolling before printing', async ({ page }) => {
    await page.setViewportSize({ width: 900, height: 1000 });
    await stubPrintData(page, makePrintData());
    await page.goto(PRINT_URL);
    await expect(page.getByTestId('print-event-name')).toBeVisible();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    // A few pixels of rounding is fine; a wide table must not push the layout.
    expect(overflow).toBeLessThanOrEqual(2);
  });

  test('A4 page geometry and break rules are declared', async ({ page, request }) => {
    await stubPrintData(page, makePrintData());
    await page.goto(PRINT_URL);
    await expect(page.getByTestId('print-event-name')).toBeVisible();

    // Read the applied rules from the CSSOM, and the stylesheet source for the
    // named page size: Chromium serialises `@page { size: A4 }` in `cssText` as
    // computed lengths, so "A4" is only observable in the source text.
    const sheets = await page.evaluate(() =>
      Array.from(document.styleSheets).map((sheet) => {
        try {
          return { href: sheet.href, rules: Array.from(sheet.cssRules).map((rule) => rule.cssText).join('\n') };
        } catch {
          return { href: sheet.href, rules: '' };
        }
      })
    );
    const css = sheets.map((s) => s.rules).join('\n');

    expect(css).toMatch(/@media\s+print/);
    expect(css).toMatch(/@page/);
    expect(css).toMatch(/break-inside\s*:\s*avoid/);
    expect(css).toMatch(/\.no-print/);

    const appSheet = sheets.find((s) => s.href && s.href.includes('globals'));
    expect(appSheet, 'the global stylesheet must be applied on this route').toBeTruthy();
    const source = await (await request.get(appSheet!.href as string)).text();
    // The named page size and the legacy `page-break-*` aliases are only
    // observable in the source: Chromium resolves `size: A4` to computed
    // lengths and folds `page-break-inside` into `break-inside` in `cssText`.
    expect(source).toMatch(/@page\s*\{[^}]*size:\s*A4/);
    expect(source).toMatch(/page-break-inside\s*:\s*avoid/);
    expect(source).toMatch(/page-break-after\s*:\s*avoid/);
  });
});