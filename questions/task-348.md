# task-348 — `/e2e` ROUGE (2ᵉ passage, après fusion de task-331) : `E2E-DETAIL-002` mobile, interaction task-331 × task-348

**Date** : 2026-10-04
**Étape** : `/e2e` (bloquante, sans exemption). Chaîne arrêtée avant `/review`. La task reste en `wip-*`.
**Verdict de la porte** : ROUGE (code 1), **1 motif bloquant**.

## Ce qui a changé depuis le 1ᵉʳ passage

`origin/develop` (task-331 mergée) a été fusionné dans les branches task-348 d'api-mail, client-blazor
et dtos-mss (DTO **514.0.0**, qui porte les deux contrats). Le clone mobile est aligné sur
`origin/develop` (`dd92872`, task-331).

- **Voie Angular : verte.** 26 réussis, 0 rouge, parité verte. `E2E-PATIENT-002` est maintenant au
  catalogue, et `E2E-SEARCH-001` est **flaky** (vert au second essai, listé, non bloquant).
- **Voie mobile : rouge.** 26 réussis, **1 rouge**, parité verte.

## Le motif

`détail — bascule texte brut / HTML` (`E2E-DETAIL-002`), `Client/Mobile/e2e/specs/functional.spec.ts:843` :
`[headless — donnée seedée attendue] mail sans corps affichable`.

- **Déterministe** : rouge aux deux essais de la voie, puis **3 fois sur 3** en `--serve-only` +
  `--grep E2E-DETAIL-002 --repeat-each 3 --retries 0`.
- **L'API rend bien le corps** : `GET /api/v1/mail/folders/INBOX/emails/content/1` → 200 en 46 à 78 ms,
  `body` 82 caractères, `bodyHtml` 84 caractères (vérifié directement contre le backend servi).
- Le test voit le corps HTML s'afficher, puis l'état `mail-body-empty` (« Aucun contenu disponible
  pour ce courrier ») devient visible. Dans `mail-body.component`, cet état ne s'affiche que si
  `hasAnyContent` est faux, c'est-à-dire si `content` n'a ni `bodyHtml`, ni `body`, ni document.
  **Le contenu détenu par le client est donc remplacé, après coup, par un contenu sans corps.**
  Candidat probable, non prouvé : la mise à jour poussée par l'enrichissement
  (`[MailEnrichmentNotifier] Sending 8 enriched emails`, juste avant la lecture du contenu).

## Pourquoi c'est une interaction, et pas le seul fait d'une task

| Combinaison | `E2E-DETAIL-002` mobile |
|---|---|
| task-348 seule (1ᵉʳ passage, mobile `a3570b8`, avant task-331) | ✅ |
| task-331 seule (son propre `## E2E log`, `archived-task-331.md`) | ✅ |
| task-348 + task-331 (ce passage) | ❌ 3/3 |

Le code de task-348 est **identique** entre le passage vert et le passage rouge. Seul task-331 est
entré : seed e2e (un message porteur d'un document sans INS), client mobile (rattachement manuel), et
api-mail. La forge ne peut pas trancher plus loin **en lecture seule** : `/e2e` ne corrige rien et ne
fait aucun checkout.

Traces : `Client/Mobile/e2e/test-results/functional-détail-—-bascule-texte-brut-HTML-headless*/`
(`trace.zip`, `error-context.md`, captures). Rapports : `%TEMP%\forge-e2e\task-348\`.

## Décisions possibles (humain)

1. **Diagnostiquer l'interaction** (recommandé). Rejouer le scénario en `--serve-only` et suivre ce qui
   remplace `content` dans `mail-detail` / `mail-body` après le chargement : événement SSE
   d'enrichissement, rechargement, `patchAttachmentLocally`. Le correctif irait dans la task qui porte
   la cause, avec un scénario prouvé rouge.
2. **Quarantaine** de `E2E-DETAIL-002` côté mobile (tag `@quarantaine` + annotation citant la task de
   correction), si tu veux laisser passer task-348 pendant le diagnostic. La décision est la tienne
   seule.

Après la décision : `/e2e task-348`, puis la chaîne reprend (`/review` → `/tech-writer`).
