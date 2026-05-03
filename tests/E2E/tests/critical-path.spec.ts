import { test, expect, type Page, type Locator } from '@playwright/test'
import { assertNoNewBackendErrors, captureNow } from '../lib/seq-errors'

/**
 * Critical-path tests — exercise the core mail actions a practitioner
 * uses every day, with a Seq backend-error check between every step.
 *
 * Each test :
 *  1. Lands on /Mail (full splitter view : folder list + inbox).
 *  2. Picks the first mail in the list as the subject under test.
 *  3. Performs an action (toggle read, toggle flag, open detail).
 *  4. Asserts the UI reflects the new state.
 *  5. Calls assertNoNewBackendErrors(t0, label) — fails if a new
 *     unexpected error landed in Seq during the action (filter list
 *     in seq-ignored-errors.json).
 *  6. Reverts the action so the test is idempotent on the real Gmail
 *     test mailbox (state-changing tests must not leave residue).
 *
 * The tests skip cleanly if the inbox is empty (real test mailbox can
 * be drained between runs).
 */

const INBOX_LOAD_TIMEOUT = 60_000

/**
 * Navigate to the full Mail page (folder list + inbox splitter, route
 * /Mail) and wait for the inbox to populate from IMAP. /emails alone
 * doesn't auto-select a folder so MailListComponent renders nothing —
 * /Mail goes through FolderListComponent which selects INBOX by
 * default and fills MailListComponent.
 *
 * Returns the Locator of the first inbox row (the wrapping
 * `<div class="email-item">`), or null if the inbox is empty / IMAP
 * didn't deliver in time. Tests that depend on at least one mail
 * should `test.skip()` when null is returned.
 */
async function gotoInbox(page: Page): Promise<Locator | null> {
	await page.goto('/Mail', { waitUntil: 'networkidle' })
	const firstMail = page.locator('div.email-item').first()
	try {
		await firstMail.waitFor({ state: 'visible', timeout: INBOX_LOAD_TIMEOUT })
		return firstMail
	} catch {
		return null
	}
}

/**
 * Click an icon button identified by its title attribute, inside a
 * mail row. The action icons (Lu/Non lu, Drapeau, etc.) sit in a
 * grid layout where neighbouring spans (UID debug, date-full) can
 * overlap them in stacking order — Playwright's actionability check
 * then refuses to click. `force: true` bypasses that check : we know
 * the icon is the intended target since we filter by title attribute,
 * and the underlying Blazor handler runs regardless of visual stacking.
 */
async function clickRowAction(row: Locator, title: string): Promise<void> {
	await row.locator(`[title="${title}"]`).first().click({ force: true })
}

test.describe('critical path — mail actions on the first inbox row', () => {
	test('toggle read → unread → read on first mail', async ({ page }, testInfo) => {
		const firstMail = await gotoInbox(page)
		test.skip(firstMail === null, 'Inbox is empty — no mail to toggle')
		if (!firstMail) return

		// MailHeader.GetRowClass appends `email-read` to the inner
		// `<tr class="email-item-detail">` when Mail.IsRead is true.
		// Read this state directly from the DOM since the outer div
		// only carries multi-select / from-patient flags.
		const firstRow = firstMail.locator('tr.email-item-detail')
		const isRead = (): Promise<boolean> =>
			firstRow.evaluate(el => el.classList.contains('email-read'))

		const wasInitiallyRead = await isRead()

		// Step 1 — flip read state.
		let t0 = captureNow()
		await clickRowAction(firstMail, 'Lu/Non lu')
		// Poll budget : 20s pour absorber la latence IMAP STORE + propagation
		// SSE → UI re-render. 10s suffit en chaud mais flake en cold-start
		// après DB rebuild (pool de sessions IMAP vide).
		await expect.poll(isRead, { timeout: 20_000 }).toBe(!wasInitiallyRead)
		await assertNoNewBackendErrors(testInfo, t0, 'toggle-read-forward')

		// Step 2 — flip back so the test is idempotent on the real mailbox.
		t0 = captureNow()
		await clickRowAction(firstMail, 'Lu/Non lu')
		await expect.poll(isRead, { timeout: 20_000 }).toBe(wasInitiallyRead)
		await assertNoNewBackendErrors(testInfo, t0, 'toggle-read-revert')
	})

	test('toggle flag → unflag on first mail', async ({ page }, testInfo) => {
		const firstMail = await gotoInbox(page)
		test.skip(firstMail === null, 'Inbox is empty — no mail to flag')
		if (!firstMail) return

		// MailHeader renders the flag Icon with class email-icon-flagged
		// when Mail.IsFlagged is true, email-icon-unflagged otherwise.
		const wasInitiallyFlagged = (await firstMail.locator('.email-icon-flagged').count()) > 0

		let t0 = captureNow()
		await clickRowAction(firstMail, 'Drapeau')
		await expect(
			firstMail.locator(wasInitiallyFlagged ? '.email-icon-unflagged' : '.email-icon-flagged')
		).toHaveCount(1, { timeout: 10_000 })
		await assertNoNewBackendErrors(testInfo, t0, 'toggle-flag-forward')

		// Revert.
		t0 = captureNow()
		await clickRowAction(firstMail, 'Drapeau')
		await expect(
			firstMail.locator(wasInitiallyFlagged ? '.email-icon-flagged' : '.email-icon-unflagged')
		).toHaveCount(1, { timeout: 10_000 })
		await assertNoNewBackendErrors(testInfo, t0, 'toggle-flag-revert')
	})

	test('open first mail in detail view', async ({ page }, testInfo) => {
		const firstMail = await gotoInbox(page)
		test.skip(firstMail === null, 'Inbox is empty — no mail to open')
		if (!firstMail) return

		// MailListComponent's row click handler runs on the inner
		// `<tr class="email-item-detail">` — clicking the wrapping div
		// can miss the handler depending on grid layout. Click the row
		// directly. On select, MailListComponent.GetRowClass appends
		// `email-selected` to the tr (different from `email-item-selected`
		// which is a multi-select-mode marker on the outer div).
		const firstRow = firstMail.locator('tr.email-item-detail')

		const t0 = captureNow()
		await firstRow.click()
		await expect(firstRow).toHaveClass(/email-selected/, { timeout: 10_000 })
		await assertNoNewBackendErrors(testInfo, t0, 'open-first-mail')
	})
})
