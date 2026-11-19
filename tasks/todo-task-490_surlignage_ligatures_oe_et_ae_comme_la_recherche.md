# todo-task-490.md — Surlignage : ligatures œ et æ comme la recherche

**Repos**: client-angular, api-mail
**Dependencies**: task-485
**Epic**: E023
**Single frontend**: true

> Suggestion de la revue de task-485 (2026-11-19), retenue par l'humain : un médecin qui tape `oedeme` trouve le
> compte rendu qui contient « œdème », mais le détail ne le surligne pas. L'inverse aussi : `cœur` ne surligne pas
> « coeur ». « œdème », « cœur », « œsophage », « fœtus » sont courants dans un texte médical.

## Objectif

Dans le détail d'un message ouvert depuis une recherche, un mot cherché est surligné qu'il soit écrit avec ou sans
ligature, exactement comme la recherche le trouve : « oedeme » surligne « œdème » et « Œdème », « cœur » surligne
« coeur ».

### Ce qui est établi

- La recherche (api-mail, `SearchTerms.Normalize`, `Api/Mail/src/Application/Helpers/SearchTerms.cs`) écrit les
  ligatures en toutes lettres avant de comparer : table `Ligatures` — `œ Œ` → `oe`, `æ Æ` → `ae`, `ß` → `ss`,
  `ø Ø` → `o`, `ł Ł` → `l`, `đ Đ` → `d`. La SQL `search_normalize` fait de même (`unaccent`).
- Le surlignage du détail (weda2, `libs/mss/src/core/utils/text-highlight.util.ts`, `foldChar`) replie par `NFD` sans
  marques diacritiques : `NFD` ne décompose pas « œ », « æ », qui restent tels quels. D'où l'écart.
- `foldText` tient déjà la table `origin` d'un caractère replié en plusieurs lettres : une ligature qui devient deux
  lettres garde sa position d'origine.
- Les extraits de la liste de résultats (positions rendues par le serveur) ne sont pas concernés.

### Règles

1. Le repliement du surlignage écrit les ligatures **comme `SearchTerms.Normalize`** : même table, **recopiée** avec
   la source citée en commentaire (consigne `code-externe-recopie`).
2. Le surlignage couvre la ligature entière dans le texte d'origine (« œ » est surligné, pas la moitié d'un caractère).
3. Les règles de task-485 (mots vides, 3 caractères, bloc d'une phrase) sont inchangées.

## Definition of Done

- [ ] Build passes (`nx build weda2`, 0 erreur).
- [ ] Tests pass (`nx test mss-lib`, `nx test weda2` : 0 échec).
- [ ] Tests unitaires de `findTermRanges` / `searchTermsOf`, chacun **vu rouge par mutation** : « oedeme » surligne
      « œdème » et « Œdème » ; « cœur » surligne « coeur » ; « oesophage » surligne « œsophage » dans un bloc avec un
      autre mot cherché ; les plages couvrent la ligature entière ; « æ », « ß » suivent la table.
- [ ] Table des ligatures recopiée de `SearchTerms.Ligatures`, source citée en commentaire, identité vérifiée.
- [ ] Scénario **E2E-SEARCH-015 v2** dans `Api/Mail/e2e/scenarios.yml` : attendu complété — la recherche « oedeme »
      surligne « œdème » dans le détail. Clients : `angular: requis`, `mobile: non-applicable` (le détail mobile ne
      surligne pas). Implémenté dans `mss-e2e`, prouvé rouge sur le code d'avant.
- [ ] Aucune donnée de santé dans les journaux (le surlignage reste côté client).

## Manual Test Plan

- Lancer l'AppHost api-mail, puis weda2 : `cd Client/Angular/front && npm run start:weda2`.
- Rechercher `oedeme` dans une boîte qui contient un compte rendu portant « œdème » : ouvrir le message, « œdème » est
  surligné.
- Rechercher `cœur` : un message qui écrit « coeur » le surligne.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — confort de lecture de la messagerie, sans exigence DSR
- **Exigences DSR honorées** : non applicable — affichage côté client seulement
- **INS** : non applicable — aucun patient manipulé ni identifié
- **Authentification PS** : inchangée — PSC / e-CPS de la session messagerie
- **Habilitations** : inchangées — le détail n'affiche que les messages de la boîte ouverte (règle 14)
- **Interop CI-SIS** : non applicable — le document CDA est affiché tel que reçu ; seul le surlignage change
- **Tracé PGSSI-S** : aucun nouvel évènement
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — aucune donnée nouvelle stockée ni transmise
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau
