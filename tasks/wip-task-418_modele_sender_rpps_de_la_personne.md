# todo-task-418 — Modèles de message : `{{SenderRPPS}}` est le RPPS de la personne qui écrit

**Repos**: client-angular
**Dependencies**: aucune
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30, mineur client. Il a été détaché de
> task-412 le 2026-10-30, sur décision humaine, après vérification sur le code (weda2 sur
> `feature/nova-mss-weda-integration`).
>
> **Une seule couche** : le mobile n'expose pas `{{SenderRPPS}}` dans ses modèles, et le serveur ne
> remplace pas les variables de modèle. Seul weda2 est concerné.

## Objectif

Un modèle de message qui cite le RPPS de l'expéditeur insère le RPPS de la personne qui écrit (le
titulaire, ou le délégataire qui écrit pour le compte de la boîte), jamais un fragment d'adresse.

## Constat vérifié (2026-10-30)

`MailComposeComponent` (weda2, `mail-compose.component.ts`) calcule `SenderRPPS` à partir de la partie
locale de l'adresse de la boîte ouverte. Pour la boîte de Virginie, le modèle insère
« virginie.medecinrpps0062267 ». Ce n'est jamais un RPPS, et jamais celui de la personne qui écrit.

Le RPPS de la personne est déjà disponible dans weda2 : `MSS_PRACTITIONER_IDENTITY().rpps`, issu de la
claim `rpps` du jeton (task-304), celui que l'onboarding affiche.

## Règles

1. `{{SenderRPPS}}` = `MSS_PRACTITIONER_IDENTITY().rpps`, le RPPS de la personne authentifiée, qu'elle
   soit titulaire, membre ou délégataire. Ce n'est jamais un dérivé de l'adresse de la boîte.
2. RPPS absent du jeton : la variable est remplacée par une chaîne vide. On n'invente rien.

## Definition of Done

- [ ] Build passes (0 errors) sur `client-angular` (code-only)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire de la substitution des variables de modèle, vu rouge sur le code d'avant :
  - avec une identité `rpps = "899700723440"` et la boîte `virginie.medecinrpps0062267@…`,
    `{{SenderRPPS}}` vaut `899700723440` ;
  - sans RPPS dans l'identité, `{{SenderRPPS}}` vaut une chaîne vide.

## Manual Test Plan

- weda2 via le faux hôte, backend `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e).
- Créer un modèle de message contenant `RPPS : {{SenderRPPS}}`.
- Le délégataire e2e ouvre la boîte du titulaire, rédige un message et applique le modèle.
- Attendu : le RPPS du délégataire, et non un morceau de l'adresse de la boîte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — exactitude de l'identité de l'émetteur
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), draft délégation ECO.1.2.9 à
  1.2.11 (identité de la personne qui écrit)
- **INS** : non applicable
- **Authentification PS** : PSC. Le RPPS vient du jeton, il n'est jamais saisi.
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : RPPS (identifiant national du professionnel), tel que publié par la claim
  PSC
- **Hébergement HDS** : non — logique cliente
- **AIPD / impact RGPD** : aucun changement de traitement

## Branches

- `client-angular` (code-only) : la forge écrit sur la branche checkoutée dans `Client/Angular/` (`feature/nova-mss-weda-integration` au /start, qui porte aussi le code non commité de task-412 et task-417) — l'humain gère branche, commit, push et PR TFS

## Develop log

- **client-angular** (code-only, `feature/nova-mss-weda-integration`, rien de commité) :
  - `mail-compose.component.ts` : `SenderRPPS` = `MSS_PRACTITIONER_IDENTITY().rpps` (injection
    optionnelle). La partie locale de l'adresse de la boîte n'est plus utilisée. Le jeton est fourni
    par `apps/weda2/src/app/app.config.ts`.
  - `mail-compose.component.spec.ts` : 3 tests (RPPS `899700723440` sur la boîte
    `virginie.medecinrpps0062267@…` ; RPPS vide ; aucune identité).
- **Vu rouge** sur le code d'avant : les 3 tests rendaient `RPPS : virginie.medecinrpps0062267`.
- **Vert** : `mss-lib` 1411/1411 (130 fichiers).
- **Build** : aucune erreur TypeScript. `mss:build:production` et `prescription:build:production` sont
  rouges sur le budget de bundle initial (+1,02 Mo, +264 ko), les mêmes valeurs qu'à task-417 :
  préexistant.
- **Passe qualité** : 3 lignes de production, rien à simplifier.
- **Règle 1b** : non applicable, aucun endpoint touché. Aucun parcours e2e créé ni modifié.

## Timings

*(généré par `tools/timing/report.sh --task task-418 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 8.7 s | — | — | — | — |
| /develop | ok | 2 min 26 s | 1 (21 s) | 1 (23 s) | — | client-angular 1B/1T |
| **Total cycle** | | **2 min 34 s** | **1 (21 s)** | **1 (23 s)** | **0 (0.0 s)** | |
