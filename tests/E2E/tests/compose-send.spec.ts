import { test, expect } from '@playwright/test'
import { assertNoNewBackendErrors, captureNow } from '../lib/seq-errors'

/**
 * Compose & send — drive the full new-mail flow end-to-end.
 *
 * Lands on /Mail (full splitter, FolderListComponent auto-selects INBOX
 * and MailListComponent populates from IMAP), opens the compose pane via
 * the "Nouveau message" button (FolderListComponent.razor:27, fires
 * MailEventService.RequestCompose() → Mail.razor switches to
 * SelectViewType.ViewCompose and renders <NewMailComponent>), fills
 * To / Subject / Body, clicks Send, and asserts the compose pane
 * unmounts on success.
 *
 * Recipient is the test-account address itself (self-send to Gmail). The
 * subject embeds an ISO timestamp so successive runs never collide and
 * a human can pinpoint a given send in the test mailbox.
 *
 * State change : every run drops one mail in the test mailbox. The
 * mailbox is dedicated to /qa, so accumulation is acceptable. The test
 * is NOT idempotent — there is no "delete the just-sent mail" cleanup
 * since that would test the deletion path rather than the send path.
 *
 * Backend-error guard : the Seq helper checks events between (open
 * compose) and (form unmount) — covers the SendMailAsync round-trip,
 * IMAP append to Sent, and any background work fired off during the
 * send.
 */

const INBOX_LOAD_TIMEOUT = 60_000
const RECIPIENT = 'pascalcabanelweda@gmail.com'

test.describe('compose & send', () => {
	test('send a mail to pascalcabanelweda@gmail.com', async ({ page }, testInfo) => {
		// Land on /Mail and wait for the inbox to populate so the user
		// session is established before we open the compose pane. Without
		// this wait the compose button is sometimes clickable before the
		// folder list has finished mounting and the click is lost.
		await page.goto('/Mail', { waitUntil: 'networkidle' })
		await page.locator('div.email-item').first().waitFor({
			state: 'visible',
			timeout: INBOX_LOAD_TIMEOUT
		})

		// Step 1 — open compose. The "Nouveau message" button lives in
		// FolderListComponent (class .compose-button — no data-testid).
		// Match by accessible name to stay robust against CSS renames.
		let t0 = captureNow()
		await page.getByRole('button', { name: /Nouveau message/i }).click()
		const composeForm = page.locator('.compose-mail')
		await composeForm.waitFor({ state: 'visible', timeout: 10_000 })
		await assertNoNewBackendErrors(testInfo, t0, 'open-compose')

		// Step 2 — fill recipient. We do NOT press Enter to materialise
		// the chip : ContactEmailInput's Enter handler races its 150ms
		// debounced contacts filter — when the dropdown still holds a
		// stale match (seeded from focus), Enter calls SelectContact on
		// the wrong row instead of AddManualAddress. Blurring the input
		// (by clicking Subject) always lands in OnBlur → AddManualAddress
		// regardless of dropdown state, so it's race-free.
		const toInput = composeForm.getByPlaceholder('destinataire@exemple.fr')
		await toInput.fill(RECIPIENT)

		// Step 3 — subject. Clicking the subject input blurs the recipient
		// input which fires OnBlur (200ms internal delay) → chip appears.
		// Subject stamp is unique per run so a human inspecting the test
		// mailbox can map a mail back to the run that produced it.
		const stamp = new Date().toISOString().replace(/[:.]/g, '-')
		const subject = `E2E send ${stamp}`
		const subjectInput = composeForm.getByPlaceholder('Objet du message')
		await subjectInput.click()
		await expect(
			composeForm.locator('.email-chip').filter({ hasText: RECIPIENT })
		).toBeVisible({ timeout: 5_000 })
		await subjectInput.fill(subject)

		// Step 4 — body. RadzenHtmlEditor renders a contenteditable area
		// with class .rz-html-editor-content. The contenteditable attribute
		// is set without a value (`contenteditable=""`), so DO NOT match
		// `[contenteditable="true"]` — the attribute exists but its value
		// isn't "true". Match by class instead.
		const editor = composeForm.locator('.rz-html-editor-content')
		await editor.click()
		await page.keyboard.type(
			`Automated send from /qa compose-send.spec at ${stamp}.`
		)

		// Step 5 — send. On success NewMailComponent calls OnComposeClosed
		// → Mail.razor flips back to SelectViewType.ViewMailList and the
		// compose pane unmounts. We assert the pane is gone within 60s
		// (covers SMTP send + IMAP append + UI rerender). The 60s budget
		// is intentionally generous because SMTP send to Gmail can take
		// 5-15s on cold connections and the IMAP append round-trip adds
		// another 3-8s on top.
		t0 = captureNow()
		await composeForm
			.locator('[data-testid="compose-send-button"]')
			.click()
		await expect(composeForm).toHaveCount(0, { timeout: 60_000 })
		await assertNoNewBackendErrors(testInfo, t0, 'send-mail')
	})
})
