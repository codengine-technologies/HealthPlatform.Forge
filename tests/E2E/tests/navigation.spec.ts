import { test, expect, type Page } from '@playwright/test'

/**
 * Navigation tour — drive the app like a real user would : land on the
 * home page once via URL, expand the sidebar, then click the menu
 * items to traverse every main route.
 *
 * Why expand the sidebar first ? Radzen's RadzenPanelMenu collapses to
 * icons-only by default (DisplayStyle=Icon). In that state the
 * menuitems' accessible name is the Material icon name (`Mail`,
 * `Folder`, `People`, `History`) — not the human label. A real user
 * who knows the app well clicks the icon directly, but for a test we
 * want to assert against semantic labels (`Messagerie`, `Patient`...) :
 * expanding the sidebar (DisplayStyle=IconAndText) makes both icon and
 * label clickable as the menuitem's accessible name. We expand once
 * at the start of the tour.
 *
 * Sidebar items (from MailModule.cs) :
 *   - Dashboard       (/)
 *   - Messagerie      (/mail)
 *   - Patient         (/patient)
 *   - Contacts        (/contacts)
 *   - Journal d'audit (/audit)
 *
 * Profile menu (top-right, from MainLayout.razor) :
 *   - Mon profil      (/profile)
 *   - Modèles         (/templates)
 *
 * On failure the assertion message names the offending step so the
 * human knows immediately which transition broke.
 */

const TEST_EMAIL = 'pascalcabanelweda@gmail.com'

/**
 * Asserts the page is in the authenticated shell — no OIDC redirect,
 * the test user's email is visible somewhere in the body (the account
 * menu always renders it).
 */
async function assertAuthenticatedShell(page: Page, label: string): Promise<void> {
	await expect(page, `step "${label}" : redirected to OIDC callback`).not.toHaveURL(/\/callbackApi/)
	await expect(page, `step "${label}" : redirected to login`).not.toHaveURL(/\/account\/login/i)

	const body = page.locator('body')
	await expect(
		body,
		`step "${label}" : test user email missing from shell — bypass auth lost`
	).toContainText(TEST_EMAIL, { timeout: 30_000 })
}

/**
 * Click a sidebar menu item by its accessible name and wait for the
 * URL to match the expected route. Works against the `menuitem` role
 * Radzen exposes for each RadzenPanelMenuItem.
 */
async function clickSidebar(page: Page, accessibleName: string | RegExp, urlPattern: RegExp): Promise<void> {
	await page.getByRole('menuitem', { name: accessibleName }).click()
	await page.waitForURL(urlPattern, { timeout: 30_000 })
}

/**
 * Open the top-right profile menu by clicking its trigger button, then
 * click the named entry inside the dropdown. RadzenProfileMenu wraps
 * each entry in a `<menuitem>` whose nested `<a>` has its label and
 * icon as `<generic>` children. The link's accessible name does not
 * propagate up through Playwright's role tree, so we target the
 * visible text directly.
 */
async function clickProfileMenu(page: Page, entry: string | RegExp, urlPattern: RegExp): Promise<void> {
	await page.getByRole('button', { name: /Profile menu/i }).click()
	await page.getByText(entry).click()
	await page.waitForURL(urlPattern, { timeout: 30_000 })
}

test('navigation tour — user clicks through every menu entry', async ({ page }) => {
	// Step 1 — initial landing (only URL-driven nav of the test).
	await page.goto('/', { waitUntil: 'networkidle' })
	await assertAuthenticatedShell(page, 'home (initial load)')

	// Expand the sidebar so labels (Messagerie, Patient, Contacts,
	// Journal d'audit) become part of each menuitem's accessible name.
	// The toggle is the first "Toggle" button rendered by RadzenSidebarToggle.
	await page.getByRole('button', { name: /^Toggle$/i }).click()

	// Step 2..5 — sidebar items, in MailModule order. After expansion
	// the menuitem accessible name is "<icon> <label>" — match by the
	// label substring.
	await clickSidebar(page, /Messagerie/i,      /\/mail/i)
	await assertAuthenticatedShell(page, 'sidebar → Messagerie')

	await clickSidebar(page, /Patient/i,         /\/patient/i)
	await assertAuthenticatedShell(page, 'sidebar → Patient')

	await clickSidebar(page, /Contacts/i,        /\/contacts/i)
	await assertAuthenticatedShell(page, 'sidebar → Contacts')

	await clickSidebar(page, /Journal d'audit/i, /\/audit/i)
	await assertAuthenticatedShell(page, "sidebar → Journal d'audit")

	// Step 6 — back home via Dashboard. Hardcoded in MainLayout
	// (icon=dashboard, label=Localizer["Dashboard"] which the FR
	// resource resolves to "Tableau de bord").
	await clickSidebar(page, /Tableau de bord/i, /^https?:\/\/localhost:7213\/?$/)
	await assertAuthenticatedShell(page, 'sidebar → Tableau de bord')

	// Step 7..8 — profile menu (top-right) entries.
	await clickProfileMenu(page, /Mon profil/i, /\/profile/i)
	await assertAuthenticatedShell(page, 'profile menu → Mon profil')

	await clickProfileMenu(page, /Modèles/i, /\/templates/i)
	await assertAuthenticatedShell(page, 'profile menu → Modèles')
})
