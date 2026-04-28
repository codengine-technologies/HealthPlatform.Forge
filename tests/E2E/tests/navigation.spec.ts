import { test, expect, type Page } from '@playwright/test'

/**
 * Navigation smoke — visit each main MSS module page under test bypass
 * and verify it renders without an OIDC redirect.
 *
 * Routes covered (pulled from the @page directives in
 * Client/Blazor/Src/Modules/Mss/Plugin/Pages/*.razor and
 * Client/Blazor/Src/Component/Shared/Pages/*.razor) :
 *
 *   /            — Index (home)
 *   /emails      — Inbox (MailListComponent)
 *   /Mail        — Mail page wrapper
 *   /Contacts    — Annuaire / contacts
 *   /templates   — Modèles de mail
 *   /Audit       — Journal d'audit
 *   /Patient     — Vue patient
 *   /profile     — Profil utilisateur
 *
 * For each, we check :
 *   - the URL did not redirect to OIDC (`/callbackApi` or `/account/login`)
 *   - the test user's email is rendered in the shell account menu
 *     (proves the authenticated layout still has the bypass identity
 *     after the navigation)
 *
 * The route shape — capital `M`/`P`/`A`/`C` — matches the @page directives
 * literally. ASP.NET Core route matching is case-insensitive but using the
 * canonical casing keeps the test aligned with the source.
 */

const TEST_EMAIL = 'pascalcabanelweda@gmail.com'

const ROUTES: Array<{ path: string; label: string }> = [
	{ path: '/',          label: 'home'      },
	{ path: '/emails',    label: 'inbox'     },
	{ path: '/Mail',      label: 'mail'      },
	{ path: '/Contacts',  label: 'contacts'  },
	{ path: '/templates', label: 'templates' },
	{ path: '/Audit',     label: 'audit'     },
	{ path: '/Patient',   label: 'patient'   },
	{ path: '/profile',   label: 'profile'   }
]

/**
 * Asserts the page is in the authenticated shell — no OIDC redirect,
 * the test user's email is visible somewhere in the body (the account
 * menu always renders it). Use this after every page.goto.
 */
async function assertAuthenticatedShell(page: Page, label: string): Promise<void> {
	await expect(page, `route ${label} : redirected to OIDC callback`).not.toHaveURL(/\/callbackApi/)
	await expect(page, `route ${label} : redirected to login`).not.toHaveURL(/\/account\/login/i)

	const body = page.locator('body')
	await expect(
		body,
		`route ${label} : test user email missing from shell — bypass auth lost`
	).toContainText(TEST_EMAIL, { timeout: 30_000 })
}

test.describe('navigation under test bypass', () => {
	for (const { path, label } of ROUTES) {
		test(`route ${label} (${path}) renders authenticated`, async ({ page }) => {
			await page.goto(path, { waitUntil: 'networkidle' })
			await assertAuthenticatedShell(page, label)
		})
	}

	test('end-to-end tour : every route in sequence keeps the session', async ({ page }) => {
		// Visiting every route back-to-back proves the auth identity
		// survives Blazor circuit transitions, not just initial load.
		for (const { path, label } of ROUTES) {
			await page.goto(path, { waitUntil: 'networkidle' })
			await assertAuthenticatedShell(page, label)
		}
	})
})
