# todo-task-306.md — Banc de charge multi-BAL : dimension « boîtes par compte », parcours avec bascule de messagerie, et non-régression stricte des références E015

**Repos**: api-mail
**Dependencies**: **task-303** (endpoints `/account/mailboxes`, garde `SESSION_MAILBOX_MISMATCH`,
upsert d'annuaire sur le chemin bypass — tout ce qui vit dans `src/`)
**Epic**: E016
**Priorité**: **2** — n'est sur le chemin critique d'aucune valeur produit, mais c'est la seule
manière de savoir ce que le multi-boîtes coûte au service avant de l'exposer à 1000 médecins.

> **Extraite de task-303** (revue du 2026-09-13). Le harnais est du JavaScript et du Python,
> sa validation est un **tir de plusieurs heures** — donc un acte humain — et il ne conditionne
> aucun écran. Le laisser dans task-303 y ajoutait ~10 fichiers d'un autre métier et poussait la
> PR `api-mail` au-delà du plafond de la règle 5.
>
> Périmètre strict : `Api/Mail/tests/loadtest-k6/`, `Api/Mail/tests/mss.mail.loadtest.seed/`,
> `Api/Mail/tools/loadtest-seed/`. **Rien dans `src/`** — ce qui s'y trouve appartient à task-303.

## Objective

Que le banc E015 sache représenter un **compte à N boîtes** et **mesurer une bascule**, sans que
la dimension nouvelle ne déplace d'un iota les références de mesure existantes quand elle vaut 1.

Deux questions auxquelles ce banc doit répondre, et auxquelles personne ne peut répondre
aujourd'hui :

1. **Que coûte la résolution du compte et de la compatibilité sur le chemin de requête ?**
   task-303 ajoute, à chaque requête authentifiée, une résolution `compte (sub) → boîtes
   compatibles`, servie par un cache. Le coût d'un **défaut de cache** n'est pas connu. Dans un
   EPIC dont la raison d'être est que le chemin de requête a saturé Postgres à 1000 médecins,
   une lecture supplémentaire par requête ne se laisse pas estimer — elle se mesure.
2. **Que coûte une bascule ?** Elle ferme un pool IMAP+SMTP et en ouvre un autre, sur une autre
   base, chez un autre opérateur. C'est un chemin **froid** par construction, et sa fréquence
   réelle est inconnue : le banc doit permettre de la faire varier.

## Contrainte gouvernante — la non-régression prime sur la nouveauté

Les rapports de référence E015 (`tests/loadtest-k6/reports/INDEX.md`, `Docs/audits/`) sont le
seul point de comparaison avant/après de tout l'EPIC. **À `MAILBOXES_PER_USER=1`, le banc doit
produire exactement les mêmes identités, les mêmes en-têtes et les mêmes bases qu'aujourd'hui.**
Une dimension par défaut qui décalerait d'un caractère le nom d'une boîte invaliderait toute la
campagne de mesure accumulée depuis juillet.

## Contenu attendu

### 1. Identités — un compte, N boîtes, **une seule identité PSC**

`lib/identity.js` rend un **compte** (`rpps`, `pscSub` — inchangés) et ses boîtes :

- boîte 1 : `loadtest-{n}@{domain}` — **nom actuel, strictement préservé** ;
- boîtes `k ≥ 2` : `loadtest-{n}-{k}@{domain}`.

Une seule `pscSub` pour toutes les boîtes d'un compte : c'est la règle métier de task-303 (même
identité PSC), et c'est aussi ce qui rend la bascule licite au banc.

`headersFor(user, sessionId, mailboxIndex)` pose `Client-Email` de la boîte choisie ; `X-Test-Bypass`,
`Client-Rpps`, `Client-Psc-Sub`, `X-PSC-Token` restent inchangés.

### 2. Réglages

| Réglage | Défaut | Effet |
|---|---|---|
| `MAILBOXES_PER_USER` (k6) / `--mailboxes-per-user` (seed) | **1** | nombre de boîtes par compte ; à 1, tir **iso** aux références |
| `JOURNEY_P_SWITCH` | **0** | probabilité qu'un passage du parcours `journey` bascule de boîte ; à 0, parcours **iso** |

### 3. La bascule simulée doit être la **vraie** bascule

Un passage qui bascule exécute la séquence de task-303, pas un simple changement d'en-tête :

1. `POST /api/v1/sync/logout` avec les en-têtes de la session **sortante** ;
2. **nouveau** `Client-Session-Id` (le harnais en tire un neuf, comme le client réel) ;
3. requêtes suivantes avec la **nouvelle** `Client-Email`.

Sans l'étape 1, le banc laisserait derrière lui un pool IMAP orphelin par bascule et mesurerait
une consommation de connexions qui n'existe pas en production. Sans l'étape 2, il se ferait
refuser par la garde `SESSION_MAILBOX_MISMATCH` — ce qui est d'ailleurs un **test utile** :
une jambe de contre-épreuve doit vérifier que le refus tombe bien.

### 4. Seed

`--mailboxes-per-user` provisionne `users × mailboxes` boîtes sur Dovecot / GreenMail, et
**pré-enregistre les rattachements** dans l'annuaire (idempotent), pour que le premier passage
du tir ne mesure pas l'upsert. Le nom de la boîte 1 est inchangé.

### 5. Restitution — `report.py`

- Ligne **« Boîtes par compte »** et **« Part de bascules »** dans l'en-tête du rapport.
- Phase **« bascule »** : nombre, durée p50/p95, et **coût de la première requête après bascule**
  (chemin froid : pool IMAP neuf, base différente).
- Ligne **« Résolution d'annuaire »** : taux de succès du cache et p95 du défaut de cache —
  c'est la réponse à la question 1 de l'Objective.

### 6. Le point à clarifier avant de coder : `MSS_ENFORCE_PSC_IDENTITY`

Le banc tire avec `MSS_ENFORCE_PSC_IDENTITY=false`. task-303 introduit **deux** contrôles
distincts qu'il ne faut pas confondre :

- le **cross-check PSC/KC** (ex-task-048), gouverné par ce drapeau ;
- le **refus de boîte non compatible** (`MAILBOX_PSC_MISMATCH`), qui est une règle
  d'appartenance, **pas** un contrôle d'identité.

**Décision de PO : le drapeau ne neutralise que le premier.** Le refus d'appartenance s'applique
toujours, banc compris — sinon le banc n'exercerait jamais la règle centrale de l'EPIC et un
défaut d'appartenance ne serait découvert qu'en production. C'est pour cela que le seed
pré-enregistre les rattachements (§4). Une jambe de contre-épreuve vérifie qu'une
`Client-Email` non rattachée est bien refusée **même** avec le drapeau à `false`.

## Definition of Done

- [ ] Build passes on api-mail (0 errors) ; tests pass (0 failures)
- [ ] **Non-régression iso (critère n°1)** : à `MAILBOXES_PER_USER=1` et `JOURNEY_P_SWITCH=0`,
      `selftest.sh` prouve que les identités, les six en-têtes et les noms de base sont
      **identiques caractère pour caractère** à ceux d'avant la task (fixture figée du jeu
      d'en-têtes attendu, comparaison stricte)
- [ ] Test seed : `--mailboxes-per-user 1` provisionne exactement les mêmes boîtes qu'avant ;
      `--mailboxes-per-user 3` en provisionne `users × 3`, la première au nom inchangé
- [ ] Test : une seule `pscSub` par compte quel que soit le nombre de boîtes
- [ ] Test : un passage avec bascule émet `POST /sync/logout` avec les **anciens** en-têtes,
      **puis** un `Client-Session-Id` neuf, **puis** la nouvelle `Client-Email` — dans cet ordre
- [ ] Test : jambe de contre-épreuve — réutiliser le `Client-Session-Id` sortant avec la nouvelle
      boîte rend **409 `SESSION_MAILBOX_MISMATCH`** (le banc sait le provoquer et le compter)
- [ ] Test : jambe de contre-épreuve — `Client-Email` non rattachée ⇒ **403 `MAILBOX_NOT_ATTACHED`**
      **même** avec `MSS_ENFORCE_PSC_IDENTITY=false`
- [ ] `report.py` : lignes « Boîtes par compte », « Part de bascules », phase « bascule »
      (p50/p95 + coût de la première requête après bascule), ligne « Résolution d'annuaire »
      (taux de cache, p95 du défaut) — fixtures + tests `test_report_*.py` pour chacune
- [ ] `report.py` : un rapport produit à `MAILBOXES_PER_USER=1` reste **lisible et comparable**
      aux rapports de référence (pas de colonne surnuméraire qui casse la lecture avant/après)
- [ ] Documentation : `Api/Mail/tests/loadtest-k6/README.md` (les deux réglages, la séquence de
      bascule, la décision `MSS_ENFORCE_PSC_IDENTITY` du §6) et skill `loadtest-skill`
      (pré-vol : annuaire joignable, rattachements pré-enregistrés)
- [ ] **Mesure au banc, jambe A — iso** (journey 1000, `MAILBOXES_PER_USER=1`,
      `JOURNEY_P_SWITCH=0`, protocole et SHA de référence par ailleurs) : login p95, erreurs et
      backends **dans l'épaisseur du trait** de la référence E015 la plus récente. **Verdict
      attendu : la résolution d'annuaire de task-303 ne coûte rien de mesurable.** Un écart de
      login p95 > 15 % est un échec de task-303, à remonter avant d'aller plus loin
- [ ] **Mesure au banc, jambe B — multi-BAL** (`MAILBOXES_PER_USER=3`, `JOURNEY_P_SWITCH=0.1`) :
      le tir tient, `0` refus `53300`, `0` `08P01`, et le rapport **chiffre pour la première fois**
      le coût d'une bascule. Rapport dans `Docs/audits/`, ligne dans
      `Api/Mail/tests/loadtest-k6/reports/INDEX.md`

> **Portée réalisable par la forge.** Le harnais, le seed, `report.py` et tous les tests
> unitaires sont dans le périmètre de `/develop`. Les **deux mesures au banc** sont des actes
> humains (tirs de plusieurs heures via le skill `loadtest-skill`, 1000 bases hydratées) :
> `/review` les trouvera non cochées — c'est attendu, pas un échec de la chaîne.

## Manual Test Plan

- **Pré-requis banc** : task-303 déployée ; Postgres 48 Go (task-296), 1000 bases hydratées,
  VM Docker dimensionnée (cf. task-298), annuaire (task-299) joignable.
- **Lancer** (skill `loadtest-skill`, mode distant) :
  `cd Api/Mail && MSS_LOADTEST=true MSS_ENFORCE_PSC_IDENTITY=false MSS_LOADTEST_MAIL_HOST=192.168.1.69 aspire run --project src/AppHost`
- **Jambe A — iso** : seed `--users 1000 --messages 0 --mailboxes-per-user 1`, puis tir
  `MAILBOXES_PER_USER=1 JOURNEY_P_SWITCH=0 USERS=1000 … TESTID=journey-1000-task306-legA-iso`.
  - **Ce que l'humain doit voir** : un rapport dont l'en-tête annonce « Boîtes par compte : 1 /
    Part de bascules : 0 % », et dont les lignes login p95, erreurs, backends max se superposent
    à la référence E015 la plus récente. **C'est le verdict qui autorise la suite.**
- **Jambe B — multi-BAL** : seed `--mailboxes-per-user 3`, tir `MAILBOXES_PER_USER=3
  JOURNEY_P_SWITCH=0.1 … TESTID=journey-1000-task306-legB-multi`.
  - **Ce que l'humain doit voir** :
    - `docker exec postgres-pgvector psql -U postgres -c "select application_name, count(*) from pg_stat_activity group by 1"`
      → total borné, aucun emballement lié aux bascules ;
    - `docker logs --since 5m postgres-pgvector | grep -c 'too many clients'` → **0** ;
    - le rapport affiche la phase « bascule » avec un p95 crédible (ouverture IMAP à froid,
      de l'ordre de la seconde) et la ligne « Résolution d'annuaire » ;
    - `SHOW POOLS` : `cl_waiting` à 0 en régime.
- **Contre-épreuves** (courtes, hors tir long) : `USERS=5` avec la jambe qui réutilise le
  `Client-Session-Id` → 409 comptés ; puis une `Client-Email` non rattachée → 403 comptés,
  **avec `MSS_ENFORCE_PSC_IDENTITY=false`**.
- **Données de test** : identités et corpus **synthétiques** du banc, aucune donnée réelle,
  aucun serveur MSSanté de production sollicité.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — capacité et robustesse du service (EPIC E015 / E016)
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur l'outillage de
  mesure
- **INS** : non applicable — le banc n'utilise que des identités et des corpus synthétiques ;
  aucune donnée patient réelle n'entre dans le harnais
- **Authentification PS** : le banc emprunte le **chemin bypass** (`X-Test-Bypass`), refusé en
  Production par construction ; il ne modifie ni n'affaiblit l'authentification réelle
- **Habilitations** : le banc pré-enregistre des rattachements **synthétiques** ; la décision du
  §6 garantit qu'il exerce la règle d'appartenance au lieu de la contourner
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : les tirs produisent des traces d'audit synthétiques, dans les bases du banc
  uniquement ; aucune donnée de santé réelle
- **Consentement patient** : non applicable
- **Sécurité / confidentialité** : aucun secret en clair dans les scripts (règle déjà posée par
  task-206 : `BYPASS_KEY` en variable, jamais en littéral) ; aucune adresse MSSanté réelle
- **Référentiels métier** : RPPS synthétiques (`9{n}`), domaines de test
- **Hébergement HDS** : non applicable — banc local, hors production
- **AIPD / impact RGPD** : inchangée — aucune donnée personnelle réelle
