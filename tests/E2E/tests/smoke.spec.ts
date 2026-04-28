import { test, expect } from '@playwright/test'

/**
 * Smoke test for the test-bypass authentication flow.
 *
 * The frontend is launched with profile `https_test`
 * (ASPNETCORE_ENVIRONMENT=Test). TestAuthService replaces the OIDC flow
 * with a mock authenticated session, and HttpRequestService injects the
 * X-Test-Bypass / Client-Email / Client-Credential-Password headers on
 * every backend call.
 *
 * If this test passes :
 *  - the frontend boots without redirecting to the OIDC login page
 *  - the inbox route renders (so the bypass header is accepted by the
 *    backend and IMAP credentials reach the api)
 */
test('shell renders under test bypass with authenticated user', async ({ page }) => {
	// Land on the inbox route. The auth bypass should let us through
	// without an OIDC redirect ; the shell is then rendered with the
	// test user's email in the account menu.
	await page.goto('/emails', { waitUntil: 'networkidle' })

	// If the bypass had failed, the page would have redirected to the
	// OIDC callback / login URL.
	await expect(page).not.toHaveURL(/\/callbackApi/)
	await expect(page).not.toHaveURL(/\/account\/login/i)

	// The shell exposes the main navigation entries (Mail / Folder /
	// People / History) — proof that the authenticated layout has
	// rendered, regardless of which sub-route landed first.
	const body = page.locator('body')
	await expect(body).toContainText(/Mail/i, { timeout: 30_000 })

	// The account menu surfaces the test user's email — the cleanest
	// proof that the test bypass auth populated HttpContext.User and
	// that the SignalR / Blazor circuit picked up the identity.
	await expect(body).toContainText(/pascalcabanelweda@gmail\.com/i, { timeout: 30_000 })
})
