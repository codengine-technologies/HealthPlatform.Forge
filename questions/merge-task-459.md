# merge-task-459 — /merge refusé : deux PRs en conflit avec `develop`

**Étape** : /merge (porte 5 — branche en retard sur `develop`). **Aucune PR n'a été mergée** (atomique).

## Constat

`develop` a reçu task-466 entre l'ouverture des PRs de task-459 et le merge :

| PR | État | Cause |
|---|---|---|
| dtos-mss #67 | `MERGEABLE` / `CLEAN` | — |
| api-mail #369 | `CONFLICTING` | task-466 (#368) touche les mêmes fichiers |
| client-mobile #125 | `CONFLICTING` | task-466 (#124) touche `e2e/specs/functional.spec.ts` et `e2e/support/e2e-backend.ts` |

## Ce que la resynchronisation doit traiter (pas seulement des marqueurs)

1. **Paquet DTO** : `develop` d'api-mail référence **607.0.0** (task-466, sans `MailDto.Reply`/`IsReport`) ; la branche
   référence **606.0.0** (task-459, sans les champs de task-466). Aucun paquet publié ne porte les deux. Il faut
   merger dtos-mss #67 (ou synchroniser sa branche), laisser la CI publier le paquet suivant, puis le référencer dans
   api-mail.
2. **Collision de migration** : `20261113120000_AddMailboxTrackingStart` (task-466, sur `develop`) et
   `20261113120000_AddMailReplies` (task-459) portent **le même horodatage**. La migration de task-459 doit être
   renumérotée après celle de task-466, avec un audit 7c (snapshot, aucune opération fantôme).
3. **Conflits de code** : `Mail.cs`, `MailDataContext.cs`, `MailRepository.cs`, `EmailBuildingService.cs`,
   `ImapService.cs`, `ServiceCollectionExtensions.cs`, `e2e/scenarios.yml`, les `packages.lock.json` ; côté mobile les
   deux fichiers du support e2e.
4. **Revalidation** : build + suite complète api-mail et mobile, puis les deux voies e2e (le catalogue et les deux
   suites ont bougé) avant de rouvrir le merge.

## Côté client-angular (code-only, pour information)

Après la reprise du stash sur `task 466` (`6d7dca93`) et la résolution du conflit de `e2e-backend.ts` :
`nx build weda2` vert, **`nx test mss-lib` rouge** — échecs dans des specs que task-459 ne touche pas (audit,
carnet de contacts, panneau de rattachement manuel, rafraîchissement de destination). À établir : rouge déjà
présent sur `task 466` seul, ou effet du merge.

## Décision attendue

Relancer la synchronisation par la forge (merge `origin/develop` dans chaque branche, paquet DTO, renumérotation de la
migration, revalidation complète, e2e), puis `/merge task-459 --i-tested` à nouveau — ou la faire à la main.
