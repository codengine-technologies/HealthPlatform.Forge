# questions/task-365.md — `/e2e` bloqué : régression ANTÉRIEURE à la task (voie Angular)

**Nature du blocage : RÉGRESSION**, sans lien avec le code de task-365. La porte bloque tout rouge
hors quarantaine (règle 4), même déjà présent sur la branche.

## Constat (2026-10-18, après réparation de l'outillage)

- Voie **mobile** : ✅ verte, 37/37, parité verte. Son rapport n'a pas été conservé (écrasé par les
  montages suivants) : à rejouer pour la porte.
- Voie **Angular** : 44 verts, **1 rouge aux deux essais**, parité verte :
  `patients — rattacher à la main un document sans INS à une fiche cherchée par son nom`
  (**E2E-PATIENT-002**), `functional.e2e.ts:206` — `locator.click: Timeout 15000ms` sur
  `attachment-confirm-ok`. La boîte de rattachement est revenue à son état initial.
  Traces : `Client/Angular/front/e2e/mss-e2e/out/test-results/functional.e2e.ts-patients-f244d--…/trace.zip`.
- Les 4 tests `E2E-SESSION-001`, `002` et `003` de la task sont **verts**, et prouvés par mutation.

## Cause

La trace contient **4 844 `POST /auth/refresh`** sur un seul test, des centaines par seconde, dès
l'obtention du jeton. `TokenRefreshSchedulerService` (task-370, commit `f710e5a9`, non modifié par
task-365) arme `setTimeout(refresh, échéance − maintenant − 30 s)`. Le jeton simulé du banc échoit en
**2099**. Ce délai dépasse le maximum de `setTimeout` (2³¹−1 ms ≈ 24,8 jours) : le navigateur le
déclenche **immédiatement**. Chaque rafraîchissement republie un jeton, qui replanifie, et ainsi de
suite. Les flux SSE et l'appariement patient sont relancés en boucle, ce qui remet la boîte de
rattachement à zéro.

En production, les jetons durent quelques minutes : le défaut est latent, mais réel. Il suffit d'une
échéance lointaine ou d'une horloge décalée.

## Décision attendue de l'humain

1. **Corriger** (recommandé) : borner le délai du planificateur à 2³¹−1 ms (`Math.min`), test unitaire
   rouge d'abord, puis rejouer `/e2e task-365` (les deux voies).
2. Ou **quarantaine** d'E2E-PATIENT-002, posée par l'humain avec une task de correction.

## Réponse (2026-10-18)

Outillage réparé par l'humain (port Flagsmith réservé par WinNAT, secret AppHost purgé). Correctif du planificateur de rafraîchissement retenu (option 1) : porte e2e verte.
