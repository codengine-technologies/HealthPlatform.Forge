# todo-task-239.md — L'enrichissement ne détient plus le verrou de session pendant le pipeline CDA : le parcours du médecin n'attend plus derrière son propre traitement

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune (task-238 touche la jambe SMTP, celle-ci la jambe IMAP —
coordination légère au moment des merges, pas de blocage)
**Priorité**: **1** — c'est LE plafond mesuré du palier 200 médecins : tant qu'il
tient, aucune re-certification 200 n'a de sens, et l'US « hydratation fiche
patient » reste indécidable (sa queue à 200 vient de cette contention).

## Objective

Qu'un médecin dont un traitement d'analyse tourne en arrière-plan puisse
continuer à consulter sa boîte : ouvrir l'inbox, lire un message, ouvrir une
fiche patient — **sans attendre que son traitement ait fini**. Aujourd'hui,
l'enrichissement détient le verrou de session IMAP pendant **tout** son
pipeline (téléchargement IMAP, extraction IHE-XDM, parsing CDA, écritures
base), alors que seule la phase de téléchargement a besoin de la session.

**Contraintes absolues** :
- **Aucun changement de contrat** : mêmes routes, mêmes réponses, même
  sémantique d'enrichissement (déduplication, générations UIDVALIDITY,
  complétude des documents produits — le contenu clinique ne disparaît jamais
  en silence, task-227).
- **Le CDA continue de transiter par `interop-cda`** et sa validation — seul le
  *moment où le verrou est tenu* change, jamais le traitement lui-même.
- La **cohérence de session IMAP est préservée** : les opérations réellement
  IMAP (SELECT/FETCH) restent sérialisées sous le verrou comme aujourd'hui.

## La mesure — re-certification K=1 du 2026-08-06 (`report-journey-certif-n200-120344`)

| Signal | Valeur | Lecture |
|---|---|---|
| Détention `imap_session` par `EnrichEmails` | **7,44 s p95**, 12,5 acq/s | le pipeline complet (réseau + parse + base) sous verrou |
| Attente `UpdateFlag` / `GetFolders` derrière | 0,88 s / 0,49 s p95 | le parcours du médecin fait la queue |
| Inbox (étape 2) à 200 médecins | p95 **4 112 ms** (cible 1 000) | ✅ à 50 et 100 — c'est la contention, pas un coût fixe |
| Contenu (`emails/content`) côté serveur | p95 max **10 000 ms** | des lectures à 25 ms p50 coincées derrière un enrich |
| Fiche patient (étape 11) à 200 | p95 4 692 ms (cible 4 000) | ✅ à 50/100 — même cause, US hydratation en attente de ce correctif |

Contexte d'instrument : ces chiffres datent du harnais corrigé (`f209ce8`) —
avant lui, l'enrichissement court-circuitait sur des contenus fantômes et ce
coût était invisible. À 50 et 100 médecins, 10 étapes sur 11 sont vertes ;
à 200, la contention fait tomber les étapes 2, 3 (p95), 6 (préexistant, task-238)
et 11.

## Remèdes demandés

1. **Réduire la portée du verrou au strict IMAP** : sous le verrou, uniquement
   le téléchargement des parties nécessaires (message + pièce jointe) ;
   extraction IHE-XDM, parsing CDA (`interop-cda`), calculs et écritures base
   se font **hors verrou**, sur les octets déjà téléchargés.
2. **Lots courts** : entre deux messages d'un même lot d'enrichissement, le
   verrou est relâché (ou re-acquis par message/sous-lot) pour laisser passer
   les gestes interactifs du médecin — l'esprit des sous-lots de task-228,
   appliqué au verrou et non plus seulement à la phase A.
3. **Instrumenter la preuve** : la table « verrou par opération » du banc doit
   montrer la nouvelle détention d'`EnrichEmails` (attendu : de 7,44 s à
   l'ordre du téléchargement seul, ~1–2 s sous latence mssante), et l'attente
   des opérations interactives (`GetFolders`, `UpdateFlag`, `GetEmailContent`)
   doit chuter en conséquence.

**Hors périmètre (décisions explicites)** : une session IMAP *dédiée* à
l'enrichissement (doublerait les sessions par praticien — le dimensionnement
Dovecot/1000 vient d'être desserré, ne pas le re-serrer sans mesure) ; toute
modification du pipeline CDA lui-même ; l'hydratation de la fiche patient
(US séparée, à re-mesurer après celle-ci).

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Zéro changement de contrat** : routes, codes HTTP, corps de réponse et sémantique d'enrichissement inchangés — tests d'intégration existants inchangés
- [ ] Unit tests : le parsing/l'écriture base s'exécutent hors verrou (test d'ordre d'appels sur le scope du verrou — mock : aucune acquisition pendant la phase parse/persist) ; le téléchargement reste sous verrou ; un échec de parse ne laisse jamais le verrou détenu
- [ ] La complétude clinique est préservée sous concurrence : un geste interactif intercalé entre deux messages d'un lot ne fait ni perdre ni dupliquer un document (test d'intégration)
- [ ] Aucune donnée de santé en clair dans les logs (les traces du verrou ne portent ni sujet, ni contenu CDA, ni INS)
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : re-certification K=1, 200 médecins, iso-conditions avec `journey-certif-n200-120344` :
  - détention `EnrichEmails` p95 **≤ 2 s** (référence : 7,44 s)
  - étape 2 (inbox) p95 **≤ 1 000 ms** à 200 médecins (référence : 4 112 ms)
  - étape 3 p95 ≤ 500 ms et `journey_warm_served_from_store` ≥ 95 % (référence : 888 ms / 99,4 %)
  - fiche patient (étape 11) : p95 re-mesuré et consigné — c'est le chiffre qui décide de l'US hydratation
  - 0 régression sur les étapes déjà vertes, erreurs < 0,1 %, vérification par base PASS

## Manual Test Plan

- Monter le banc : skill `loadtest-skill` (profil `https-load-test`)
- Depuis une session, déclencher un enrichissement d'un lot (`POST
  .../emails/enrich/sync` sur 10 UIDs frais) et, **pendant** qu'il tourne,
  enchaîner depuis la même identité : `GET /mail/folders`, lecture d'un contenu
  déjà servi base, `mark read`
- Vérifier : les gestes interactifs répondent en dizaines/centaines de ms
  (aujourd'hui : bloqués jusqu'à ~7 s) ; l'enrichissement aboutit avec le même
  nombre de documents médicaux qu'avant (comparer `hasMedicalDocuments` sur le
  lot)
- Contre-épreuve chiffrée : tir de re-certification K=1 200 médecins (voir DOD)
  et lecture de la table « Verrou de session `imap_session`, par opération »

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — optimisation interne de concurrence
- **Exigences DSR honorées** : non applicable — aucun changement fonctionnel ; la complétude du traitement des documents (CI-SIS) est explicitement préservée par la DOD
- **INS** : non applicable — aucun traitement d'identité modifié ; l'identito-vigilance du rattachement documentaire est inchangée
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable — le CDA transite toujours par `interop-cda` avec la même validation ; seul le moment de détention du verrou change
- **MSSanté** : non applicable — la jambe SMTP n'est pas touchée (task-238) ; les sessions IMAP restent authentifiées à l'identique
- **Tracé PGSSI-S** : inchangé — mêmes évènements de traitement ; les métriques de verrou n'exposent aucune donnée patient
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données
