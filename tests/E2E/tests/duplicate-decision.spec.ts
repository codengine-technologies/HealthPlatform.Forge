import { test, expect, type APIRequestContext } from '@playwright/test'

/**
 * task-013 — duplicate-decision persistence regression test.
 *
 * Reproduces the bug where confirming a duplicate (POST
 * /duplicate-decision { isDuplicate: true }) did not survive a fresh
 * GET /emails/content/{uid} : the practitioner saw the banner go blue
 * (optimistic patch on the FE), navigated away, came back — and the
 * banner was yellow again because the API kept serving
 * `duplicateConfirmed: false` despite the DB column being persisted
 * to `true`.
 *
 * The test is API-only (no browser) and uses the X-Test-Bypass header
 * recognised by RequestHelper.TryTestBypass when ASPNETCORE_ENVIRONMENT
 * is non-Production. Playwright's APIRequestContext speaks directly to
 * the api-mail process at API_BASE_URL (defaults to https://localhost:7012,
 * matching api-mail's https launchSettings profile).
 *
 * Flow :
 *   1. Scan INBOX UIDs (paged, top -> bottom).
 *   2. For each mail, GET /emails/content/{uid} until we find a
 *      medical document whose `duplicateOfId` is non-null AND
 *      `isDuplicate` is true (i.e. the duplicate signal is currently
 *      active — Pending or Confirmed, both fine for this test).
 *   3. Force the doc into Pending state by POSTing isDuplicate=false
 *      then back to "decision pending" is impossible via the public
 *      API (the endpoint is binary : Confirm / Reject). So we instead
 *      capture the current `duplicateConfirmed` flag, POST the
 *      OPPOSITE verdict, then POST `isDuplicate: true` (Confirm) and
 *      assert the GET reflects it.
 *   4. Refetch /emails/content/{uid} and assert
 *      `duplicateConfirmed === true` for that doc.
 *
 * Skips cleanly when the inbox has no duplicate-flagged document.
 *
 * Note : the bypass user inherits its DB from the Client-Email header.
 * Set TEST_USER_EMAIL to whichever mailbox actually contains a known
 * duplicate (defaults to the same account the Blazor compose-send
 * test uses).
 */

const API_BASE_URL = process.env.API_BASE_URL ?? 'https://localhost:7012'
const TEST_BYPASS_KEY = process.env.TEST_BYPASS_KEY ?? 'e2e-test-bypass-key-12345'
const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL ?? 'pascalcabanelweda@gmail.com'
const TEST_FOLDER = process.env.TEST_FOLDER ?? 'INBOX'

// How many UIDs to scan before giving up (worst case : every mail is
// fetched once). Capped to keep the test under the global 60 s timeout
// when the inbox is large.
const MAX_UIDS_TO_SCAN = 100

interface MedicalDocumentDto {
	id: number
	isDuplicate?: boolean
	duplicateOfId?: number | null
	duplicateConfirmed?: boolean
}

interface MailContentDto {
	uid: number
	medicalDocuments: MedicalDocumentDto[]
}

interface FolderDto {
	path: string
	uids?: number[]
}

function bypassHeaders(): Record<string, string> {
	return {
		'X-Test-Bypass': TEST_BYPASS_KEY,
		'Client-Email': TEST_USER_EMAIL,
		'Client-Session-Id': `e2e-duplicate-decision-${Date.now()}`,
		Accept: 'application/json'
	}
}

async function getFolder(api: APIRequestContext, folder: string): Promise<FolderDto | null> {
	const resp = await api.get(`${API_BASE_URL}/api/v1/mail/folders/${encodeURIComponent(folder)}`, {
		headers: bypassHeaders()
	})
	if (!resp.ok()) return null
	return (await resp.json()) as FolderDto
}

async function getEmailContent(
	api: APIRequestContext,
	folder: string,
	uid: number
): Promise<MailContentDto | null> {
	const resp = await api.get(
		`${API_BASE_URL}/api/v1/mail/folders/${encodeURIComponent(folder)}/emails/content/${uid}`,
		{ headers: bypassHeaders() }
	)
	if (!resp.ok()) return null
	return (await resp.json()) as MailContentDto
}

async function postDuplicateDecision(
	api: APIRequestContext,
	documentId: number,
	isDuplicate: boolean
): Promise<number> {
	const resp = await api.post(
		`${API_BASE_URL}/api/v1/medical-documents/${documentId}/duplicate-decision`,
		{
			headers: { ...bypassHeaders(), 'Content-Type': 'application/json' },
			data: { isDuplicate }
		}
	)
	return resp.status()
}

interface DuplicateCandidate {
	uid: number
	doc: MedicalDocumentDto
}

/**
 * Scan INBOX UIDs (most-recent-first as returned by the folder
 * endpoint) and return the first medical document carrying the
 * duplicate signal — `duplicateOfId` populated, regardless of the
 * current Confirmed/Rejected verdict (the test will overwrite it).
 */
async function findDuplicateCandidate(
	api: APIRequestContext,
	folder: string
): Promise<DuplicateCandidate | null> {
	const folderDto = await getFolder(api, folder)
	if (!folderDto?.uids || folderDto.uids.length === 0) return null

	const uids = folderDto.uids.slice(0, MAX_UIDS_TO_SCAN)
	for (const uid of uids) {
		const content = await getEmailContent(api, folder, uid)
		if (!content) continue

		const doc = content.medicalDocuments.find(
			d => d.duplicateOfId != null && d.isDuplicate === true
		)
		if (doc) return { uid, doc }
	}
	return null
}

test.describe('duplicate-decision persistence (task-013)', () => {
	test('confirming a duplicate persists across a fresh /emails/content fetch', async ({
		playwright
	}) => {
		const api = await playwright.request.newContext({ ignoreHTTPSErrors: true })

		try {
			// Step 1 — discover a duplicate doc on the test mailbox.
			const candidate = await findDuplicateCandidate(api, TEST_FOLDER)
			test.skip(
				candidate === null,
				`No duplicate document found in ${TEST_FOLDER} for ${TEST_USER_EMAIL} — ` +
					'seed a CDA twice on this mailbox to enable the test.'
			)
			if (!candidate) return

			const { uid, doc } = candidate

			// Step 2 — flip the verdict to its opposite first, so the
			// final Confirm step is guaranteed to be a real state change
			// (not a no-op when the doc is already Confirmed). The endpoint
			// is binary : true → Confirmed, false → Rejected.
			const seedStatus = await postDuplicateDecision(api, doc.id, false)
			expect(seedStatus, 'seed Reject must succeed').toBe(204)

			// Step 3 — Confirm.
			const confirmStatus = await postDuplicateDecision(api, doc.id, true)
			expect(confirmStatus, 'Confirm must succeed').toBe(204)

			// Step 4 — refetch and assert. This is the regression check :
			// after confirming, the next GET must serve duplicateConfirmed=true
			// for this document. Before the fix the API kept serving
			// `false` (cache or projection bug, depending on the build).
			const refreshed = await getEmailContent(api, TEST_FOLDER, uid)
			expect(refreshed, 'refetch must succeed').not.toBeNull()
			const refreshedDoc = refreshed!.medicalDocuments.find(d => d.id === doc.id)
			expect(refreshedDoc, `doc ${doc.id} missing on refetch`).toBeDefined()
			expect(
				refreshedDoc!.isDuplicate,
				'isDuplicate must remain true after Confirm'
			).toBe(true)
			expect(
				refreshedDoc!.duplicateConfirmed,
				'duplicateConfirmed must be true after Confirm — banner should be Confirmé'
			).toBe(true)
		} finally {
			await api.dispose()
		}
	})

	test('rejecting a duplicate persists across a fresh /emails/content fetch', async ({
		playwright
	}) => {
		const api = await playwright.request.newContext({ ignoreHTTPSErrors: true })

		try {
			const candidate = await findDuplicateCandidate(api, TEST_FOLDER)
			test.skip(
				candidate === null,
				`No duplicate document found in ${TEST_FOLDER} for ${TEST_USER_EMAIL}`
			)
			if (!candidate) return

			const { uid, doc } = candidate

			// Confirm first so Reject is a real state change.
			const seedStatus = await postDuplicateDecision(api, doc.id, true)
			expect(seedStatus).toBe(204)

			const rejectStatus = await postDuplicateDecision(api, doc.id, false)
			expect(rejectStatus).toBe(204)

			const refreshed = await getEmailContent(api, TEST_FOLDER, uid)
			expect(refreshed).not.toBeNull()
			const refreshedDoc = refreshed!.medicalDocuments.find(d => d.id === doc.id)
			// After Reject, the derived isDuplicate flips to false (banner
			// hidden) and duplicateConfirmed must also be false. The doc
			// itself may still appear in the medicalDocuments list (it
			// belongs to the mail), only the duplicate signal is cleared.
			if (refreshedDoc) {
				expect(
					refreshedDoc.isDuplicate ?? false,
					'isDuplicate must be false after Reject'
				).toBe(false)
				expect(
					refreshedDoc.duplicateConfirmed ?? false,
					'duplicateConfirmed must be false after Reject'
				).toBe(false)
			}
		} finally {
			await api.dispose()
		}
	})
})
