# task-377 — arbitrage humain requis : le mobile dans le catalogue e2e

> Écrit par `/develop` le 2026-10-28. Le reste de la task est implémenté, testé et poussé
> (api-mail) ou laissé non commité (client-angular). La chaîne continue. Ce point bloquera `/e2e`
> si rien n'est décidé.

## Le constat

La DoD demande :

- « Scénario E2E-BIO-002 […] ajouté (angular `requis` ; mobile : `non-applicable` si la puce
  n'existe pas sur mobile, **à confirmer**) » ;
- « Scénario E2E-PATIENT-001 versionné : la vue « Mails du patient » reste ouverte et paginée ».

Vérification faite sur `Client/Mobile` :

1. **La puce « Bio à acquitter » existe sur le mobile**
   (`features/mail/components/inbox-biology-ack-chip`), avec **le même défaut** : elle émet la liste
   des UID en attente, et `mail-state.service.ts` (`biologyAckFilterUids`) filtre les seuls messages
   chargés. La condition « non-applicable si la puce n'existe pas » est donc fausse. Le catalogue
   porte **E2E-BIO-002 `mobile: requis`**, ce qui est l'état réel.
2. **Le mobile n'a pas de vue « Mails du patient »** : le dossier d'un patient s'y lit dans la fiche
   (`patient-timeline`). E2E-PATIENT-001 (« Afficher la vue patients ») est `requis` sur le mobile.
   Le monter en version 2 pour un écran que le mobile n'a pas mettrait le mobile en `StaleVersion`,
   sans rien qu'il puisse corriger. J'ai donc **créé E2E-PATIENT-004** (angular `requis`, mobile
   `non-applicable` : écran absent), et laissé E2E-PATIENT-001 en version 1. **Écart à la DoD**,
   à valider.

`client-mobile` n'est pas dans les `**Repos**` de la task : la forge n'y a rien écrit (règle 6).

## Conséquence — constatée par `/e2e` le 2026-10-28 : chaîne arrêtée (motif « parité »)

La porte rend **ROUGE, 1 motif** : `MissingRequired [mobile] E2E-BIO-002`. Ce n'est **pas** une
régression :

| Voie | Suite | Parité de la colonne |
|---|---|---|
| mobile | 47 verts, 0 flaky, 0 rouge | rouge : E2E-BIO-002 absent de la suite mobile |
| angular | 58 verts, 0 flaky, 0 rouge (E2E-BIO-002 et E2E-PATIENT-004 compris) | verte |

Le détail (matrice complète) est dans le `## E2E log` du task file. `/sonar` (QG OK, rien à corriger)
et `/lint-angular` (0 erreur) sont passés ; `/review` n'est pas lancé.

Les deux sorties légitimes d'un écart de parité sont les options A et B ci-dessous (C contourne
l'étape). Une fois la décision prise, relancer `/e2e task-377` (la voie Angular verte sera réutilisée
si rien n'a bougé), qui enchaînera `/review`.

## Décisions possibles (humain seul)

- **A. Étendre la task au mobile** : ajouter `client-mobile` aux `**Repos**`. La puce mobile passe
  par `GET biology-acks/pending-mail-uids/page` (route livrée ici), et le test E2E-BIO-002 est écrit
  dans `Client/Mobile/e2e/specs/functional.spec.ts`. Relancer `/develop task-377`.
- **B. Divergence temporaire** sur E2E-BIO-002 pour le mobile (raison + task de résorption, à
  écrire au catalogue), et une task mobile dédiée.
- **C. Bypass `/e2e`** pour cette task (`**E2E**: bypass — décision humaine du …`).

Et, quel que soit le choix : **E2E-PATIENT-004 au lieu d'une version 2 d'E2E-PATIENT-001**, oui ou
non ?

## Décision humaine — 2026-10-28

- **Option A** : `client-mobile` ajouté aux `**Repos**`, branche `feat/task-377-bio-a-acquitter-liste-recherche-fiables` créée depuis `origin/develop` et poussée. `/develop task-377` relancé pour la puce mobile et le test E2E-BIO-002 mobile.
  - Fait : commit mobile `855053a`, poussé. La puce mobile pagine sur les UID en attente avec la pagination existante du mobile, sans la route paginée (le mobile connaît déjà tous les UID en attente). Détail dans le `## Develop log`.
- E2E-PATIENT-004 au lieu d'une v2 d'E2E-PATIENT-001 : pas d'objection exprimée, état conservé (à confirmer au HAG).

## Nouvel arrêt — 2026-10-28 22:38 : le plan de contrôle a changé sous la chaîne (outillage, pas la task)

Pendant la relance de `/develop`, le plan de contrôle a été synchronisé avec `origin/develop`
(reflog : `merge origin/develop` à 22:31 et 22:37, travail de task-402) **hors de cette session**.
Constaté à 22:38 :

- les modifications non commitées du plan de contrôle ont disparu de l'arbre : sections du task file
  de task-377 (Branches, Develop/Sonar/Lint/E2E log), ce fichier `questions/task-377.md`, la ligne
  task-377 de `conventions/e2e.md` (et les autres fichiers modifiés ou non suivis listés au début de
  la session) ; l'autostash `stash@{0}` (22:37) ne les contient pas ;
- **`metrics/timings.jsonl` est en conflit (`UU`)** : la réapplication de l'autostash a buté dessus.

Ce qui a été fait : les fichiers de task-377 sont **restaurés** depuis les copies de session (ce
fichier, les sections du task file, la ligne de `conventions/e2e.md`). Aucune opération git sur le
plan de contrôle, **le conflit de `metrics/timings.jsonl` est laissé tel quel** : il appartient à
l'opération en cours. Les dépôts de code ne sont pas touchés (api-mail et mobile poussés, Angular
non commité intact).

Pour reprendre :

1. Résoudre `metrics/timings.jsonl` (journal en ajout seul : garder les deux côtés, puis
   `git stash drop` de l'autostash une fois vérifié), ou me demander de le faire ;
2. Relancer `/lint-mobile task-377`, qui enchaîne `/e2e` → `/review` → `/tech-writer`.
