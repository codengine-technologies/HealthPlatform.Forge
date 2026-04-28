import { defineConfig, devices } from '@playwright/test'

/**
 * E2E Playwright config for HealthPlatform.
 *
 * The /qa agent (agents/qa.md) starts the backend (api-mail, port 5052)
 * and the frontend (client-blazor, https://localhost:7213) in test bypass
 * mode BEFORE running this suite — so we set webServer to undefined and
 * just point the browser at the running frontend.
 *
 * Self-signed dev cert → ignoreHTTPSErrors. Tests run serial (workers=1)
 * because the backend keeps shared IMAP state per test session.
 */
export default defineConfig({
	testDir: './tests',
	fullyParallel: false,
	workers: 1,
	retries: 0,
	timeout: 60_000,
	reporter: [['list'], ['html', { open: 'never' }]],
	use: {
		baseURL: 'https://localhost:7213',
		ignoreHTTPSErrors: true,
		trace: 'on-first-retry',
		video: 'retain-on-failure',
		screenshot: 'only-on-failure'
	},
	projects: [
		{
			name: 'chromium',
			use: {
				...devices['Desktop Chrome'],
				// PW_SLOW_MO=ms slows each Playwright action by `ms` milliseconds —
				// useful when running with --headed to actually see what happens.
				// Defaults to 0 (no slowdown).
				launchOptions: {
					slowMo: Number(process.env.PW_SLOW_MO ?? 0)
				}
			}
		}
	]
})
