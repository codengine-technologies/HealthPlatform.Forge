import { defineConfig, devices } from '@playwright/test'
import 'dotenv/config'

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
 *
 * `dotenv/config` loads tests/E2E/.env at startup so SEQ_API_KEY (and
 * any future env-driven knob) is picked up by the worker process. The
 * .env file is gitignored — credentials stay local.
 */
export default defineConfig({
	testDir: './tests',
	fullyParallel: false,
	workers: 1,
	// 1 retry : SMTP/IMAP cold-start (DB freshly rebuilt, MailKit session not
	// yet pooled, Aspire containers warm-up) makes the first run of state-
	// changing tests flaky with sub-30s assertions. The second run reuses the
	// established IMAP session and is consistently fast (<10s).
	retries: 1,
	// Test global timeout : 90s = 60s pour la majorité des tests + 30s de
	// budget pour les scenarii compose-send / toggle-read qui font du round-
	// trip serveur (SMTP send + IMAP append OR IMAP STORE + SSE propagation).
	timeout: 90_000,
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
