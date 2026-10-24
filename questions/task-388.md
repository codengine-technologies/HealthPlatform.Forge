# task-388 — /e2e rouge : E2E-DETAIL-001 (mobile), instabilité récurrente

**Nature du blocage** : régression au sens de la porte (un test rouge après `retries: 1`, hors quarantaine).
**Lien avec la task** : aucun démontré. L'extension (h)(i)(j) ne touche ni le transfert ni l'envoi. L'étape du test
qui utilise la rédaction modifiée passe, et le même échec existait avant ce changement.

## Constat

- Test : `Client/Mobile/e2e/specs/functional.spec.ts:505` (E2E-DETAIL-001 v3), étape 3 : transférer un message à
  deux « scan.pdf » à « robert », puis attendre sa réception.
- Échec : « le transfert arrive » (`:594`), aux deux essais. Côté serveur, tous les `POST /api/v1/mail/sendmail`
  répondent 200 (Seq) ; le message envoyé n'apparaît jamais dans la boîte.
- Historique :

  | Run | Résultat |
  |---|---|
  | 2026-10-23, run 1 | rouge (`:594`, puis `:574`) |
  | 2026-10-23, relance | flaky (rouge au 1er essai, vert au 2e) |
  | 2026-10-24 matin | vert |
  | 2026-10-24 après-midi | rouge (`:594` deux fois) |

  Le test est inscrit au registre des flaky (`conventions/e2e.md`).
- Traces : `Client/Mobile/e2e/test-results/functional-détail-—-Répond-…-headless/trace.zip` (et `-retry1`).

## Hypothèse (non prouvée)

À l'étape 3, le test clique sur la première suggestion « robert » puis remplit l'objet et envoie, **sans attendre la
puce du destinataire** (`compose-to-chip-0`), ce que fait l'étape 1. Si le clic ne prend pas, le texte « robert » est
envoyé comme adresse (task-376 : une saisie sans Entrée part à l'envoi). L'envoi est accepté, mais rien n'est reçu.
La trace ne conserve ni le corps de la requête ni les puces, donc l'hypothèse n'est pas vérifiée.

## Décision attendue (l'une des deux)

1. **Quarantaine** d'E2E-DETAIL-001 côté mobile (tag `@quarantaine` + annotation qui cite une task de correction),
   le temps de stabiliser le test, puis je reprends `/e2e` → `/review`.
2. **Je stabilise le test d'abord** dans le cadre de task-388 : attendre la puce du destinataire à l'étape 3 comme à
   l'étape 1, et vérifier l'hypothèse en journalisant le destinataire envoyé. Puis je rejoue `/e2e`.
