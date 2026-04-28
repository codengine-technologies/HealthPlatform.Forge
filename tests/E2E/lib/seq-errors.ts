import { type TestInfo } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Helper to query Seq for backend errors during a test step and assert
 * none of them are unexpected (i.e. not in the project-tracked ignore
 * list).
 *
 * Designed for use between Playwright steps that drive the UI : capture
 * a timestamp BEFORE the action with `captureNow()`, run the action,
 * then `await assertNoNewBackendErrors(testInfo, t0, 'step label')` to
 * surface any new server-side error.
 *
 * Targets the local Seq HTTP API (default `http://localhost:5341`,
 * Seq UI + /api/events). This is intentionally NOT the same env var
 * the api-mail process uses to ship logs : api-mail reads `SEQ_URL`
 * which points at the ingestion port (5342 on the host, mapped to
 * 5341 inside the container). Re-using `SEQ_URL` here would send our
 * query to the ingestion endpoint, which has no /api/events handler
 * (404 with no body). The helper uses `SEQ_QUERY_URL` so the two
 * concepts can coexist in the same shell.
 *
 * Authentication : Seq 2025.x requires an API key for the events
 * endpoint (anonymous reads return 401). Set SEQ_API_KEY in the
 * environment (or in `tests/E2E/.env`, gitignored) before running :
 *
 *   1. Open http://localhost:5341 in a browser, login as admin
 *      (default password from AppHost.cs : `admin`)
 *   2. Settings > API Keys > Create — give it Read permission
 *   3. Copy the token into tests/E2E/.env :
 *        SEQ_API_KEY=tok_xxxxxxxxxxxx
 *      (loaded automatically by dotenv via playwright.config.ts)
 *
 * Without SEQ_API_KEY the helper logs a warning and silently skips
 * the assertion rather than failing the test (Seq access shouldn't
 * block /qa). Tests pass but lose the backend-error guard.
 */

const SEQ_URL = process.env.SEQ_QUERY_URL ?? 'http://localhost:5341'
const SEQ_API_KEY = process.env.SEQ_API_KEY ?? ''

interface SeqProperty {
	Name: string
	Value: unknown
}

interface SeqEvent {
	Timestamp: string
	Level: string
	RenderedMessage?: string
	MessageTemplate?: string
	Properties: SeqProperty[]
	Exception?: string
	Id?: string
}

interface IgnorePattern {
	pattern: string
	reason: string
	since: string
}

let cachedIgnored: IgnorePattern[] | null = null

function loadIgnored(): IgnorePattern[] {
	if (cachedIgnored !== null) return cachedIgnored
	const path = join(__dirname, '..', 'seq-ignored-errors.json')
	try {
		cachedIgnored = JSON.parse(readFileSync(path, 'utf-8')) as IgnorePattern[]
	} catch {
		cachedIgnored = []
	}
	return cachedIgnored
}

function isIgnored(event: SeqEvent, patterns: IgnorePattern[]): boolean {
	const haystack = [
		event.RenderedMessage ?? '',
		event.MessageTemplate ?? '',
		event.Exception ?? '',
		...event.Properties.map(p => `${p.Name}=${String(p.Value)}`)
	].join(' | ')
	return patterns.some(p => haystack.includes(p.pattern))
}

async function fetchErrors(sinceUtc: Date): Promise<SeqEvent[] | null> {
	const params = new URLSearchParams({
		filter: "@Level in ['Error', 'Fatal'] and ApplicationName = 'mss.mail.api'",
		fromDateUtc: sinceUtc.toISOString(),
		count: '50'
	})
	const url = `${SEQ_URL}/api/events?${params.toString()}`
	const headers: Record<string, string> = { Accept: 'application/json' }
	if (SEQ_API_KEY) headers['X-Seq-ApiKey'] = SEQ_API_KEY

	try {
		const resp = await fetch(url, { headers })
		if (!resp.ok) {
			console.warn(`[seq-errors] Seq query returned ${resp.status} — skipping check`)
			return null
		}
		const body = (await resp.json()) as { Events?: SeqEvent[] } | SeqEvent[]
		return Array.isArray(body) ? body : (body.Events ?? [])
	} catch (err) {
		console.warn(`[seq-errors] Seq unreachable at ${SEQ_URL} — skipping check`, err)
		return null
	}
}

/**
 * Capture the current UTC time. Pass it to assertNoNewBackendErrors
 * after the action that follows.
 */
export function captureNow(): Date {
	return new Date()
}

/**
 * Query Seq for backend errors emitted since `sinceUtc`, filter out
 * patterns listed in `tests/E2E/seq-ignored-errors.json`, and fail the
 * test if any unexpected error remains. Failed tests get the full
 * unexpected-error JSON attached so the human can triage.
 *
 * If Seq is unreachable or returns an auth error, the assertion is
 * silently skipped (warning printed) — Seq downtime shouldn't block
 * /qa.
 *
 * Adds a 500 ms wait before querying to let Seq ingest events emitted
 * during the previous step.
 */
export async function assertNoNewBackendErrors(
	testInfo: TestInfo,
	sinceUtc: Date,
	stepLabel: string
): Promise<void> {
	await new Promise(resolve => setTimeout(resolve, 500))

	const events = await fetchErrors(sinceUtc)
	if (events === null) return

	const ignored = loadIgnored()
	const unexpected = events.filter(e => !isIgnored(e, ignored))

	if (unexpected.length > 0) {
		const safeLabel = stepLabel.replace(/[^a-z0-9]+/gi, '-')
		await testInfo.attach(`seq-errors-after-${safeLabel}.json`, {
			contentType: 'application/json',
			body: Buffer.from(JSON.stringify(unexpected, null, 2))
		})
		const preview = unexpected
			.slice(0, 3)
			.map(e => `  - [${e.Level}] ${e.RenderedMessage ?? e.MessageTemplate ?? '(no message)'}`)
			.join('\n')
		throw new Error(
			`${unexpected.length} new backend error(s) after step "${stepLabel}" :\n${preview}\n` +
			`(see attachment seq-errors-after-${safeLabel}.json for full details)`
		)
	}
}
