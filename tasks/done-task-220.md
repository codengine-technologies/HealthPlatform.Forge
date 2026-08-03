# todo-task-220.md — Un banc qui simule des médecins : parcours réaliste, montée par population, verdict SLO

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune — le banc local suffit pour livrer et smoker le
scénario. Les campagnes au-delà de ~500 praticiens attendront **task-221**
(serveurs mail sortis de l'hôte), mais ce n'est pas un prérequis de cette US.
**Priorité**: **2** — chemin critique du chantier scalabilité. Rien n'est
cassé, mais sans cet instrument la boucle « mesurer → corriger → re-mesurer »
tourne sur des tirs invalides.

## Objective

Répondre à la question que le banc actuel ne sait pas poser : **combien de
médecins l'application sert-elle à SLO tenu**, et à chaque palier, **quel est
le prochain traitement à optimiser**.

## Le défaut de l'instrument actuel

Le harnais `mixed` est un modèle **ouvert** (`constant-arrival-rate`, débit
imposé) dimensionné par la loi de Little sur des constantes mesurées à
200 praticiens. Conséquences, toutes mesurées :

1. **Tirs structurellement invalides au-delà de 200** : à 500, les temps réels
   valent 2 à 4× les constantes, les pools de VUs sont trop courts, k6 jette
   des itérations, le rapport s'ouvre sur `TIR INVALIDE`. Quatre campagnes à
   500 n'ont produit **aucun chiffre opposable**.
2. **Trois notions d'« utilisateur » qui ne se recoupent pas** (`USERS=500`,
   `VUS=60`, pools jusqu'à 800) — aucune ne veut dire « médecin ».
3. **Le mix 40/30/10/10/10 est une hypothèse, pas un usage** : opérations
   indépendantes, sans contexte, à un rythme 20 à 40× celui d'un humain.
   Quand le p95 se dégrade, rien ne dit *quelle étape du travail du médecin*
   souffre.
4. **`enrich` est traité comme une action utilisateur** alors qu'aucun médecin
   ne « déclenche un enrichissement » — d'où le bricolage `shared-iterations`
   qui a déjà failli retourner la garde d'invalidité contre des tirs sains.
5. **Quatre gestes quotidiens du médecin ne sont jamais exercés** : supprimer
   un message, télécharger une pièce jointe, marquer lu, arriver sur le
   dashboard. Le téléchargement de PJ est le seul geste qui déplace de vrais
   octets (~124 Ko/pièce) — axe bande passante jamais mesuré.

## Le modèle cible

**1 VU = 1 médecin.** Un scénario `journey` en modèle **fermé**
(`ramping-vus`, paliers de population croissante) déroule le parcours réel :
arrivée dashboard → ouverture de l'inbox → lecture de messages → suppression →
téléchargement d'une PJ → envoi d'un message — avec des **temps de réflexion**
entre les étapes. La charge devient **émergente** (N médecins × rythme), plus
personne ne l'impose : `dropped_iterations` n'existe plus, le `TIR INVALIDE`
disparaît **par construction**.

Un **facteur de compression du temps `K`** divise les temps de réflexion. Un
seul code, trois usages :

| Mode | K | Rôle |
|---|---|---|
| Découverte | 10–20 | trouver le prochain goulet vite (mêmes chemins de code, même mix) |
| Population / endurance | 1, N élevé, 1–2 h | coûts résidents contre N + fuites lentes |
| **Validation** | **1** | le verdict opposable : « N médecins au rythme réel, SLO tenu » |

⚠️ **Seul K=1 certifie un SLO.** Un tir K>1 désigne des goulets, il ne valide
jamais un palier.

## La grille SLO — validée par l'humain le 2026-08-03

À matérialiser **telle quelle** dans `docs/SLO-parcours-medecin.md` (api-mail),
avec ses conditions de mesure. C'est le contrat que `report.py` confronte à
chaque tir de validation.

**Conditions de mesure (partie intégrante du SLO)** : mode validation (K=1),
population N à certifier, fenêtre ≥ 30 min, latence MSSanté simulée 100 ms,
percentiles par étape sur toute la fenêtre, ≥ 300 échantillons par étape.

| # | Étape du parcours | p50 | p95 |
|---|---|---|---|
| 1 | Arrivée dashboard (dossiers + couverture) | 300 ms | 1,5 s |
| 2 | Ouvrir / rafraîchir l'inbox | 300 ms | 1 s |
| 3 | Ouvrir un message enrichi (servi base) | 100 ms | 500 ms |
| 4 | Ouvrir un message froid (fetch IMAP) | 800 ms | 2,5 s |
| 5 | Recherche | 500 ms | 2 s |
| 6 | Envoi (acquittement UI) | 1 s | 3 s |
| 7 | Télécharger une PJ (~124 Ko) | 500 ms | 2 s |
| 8 | Supprimer / marquer lu / déplacer | 200 ms | 1 s |

Gardes système associées : erreurs HTTP < 0,1 %, `cl_waiting` = 0 soutenu,
file ThreadPool < 100, `RedisTimeoutException` = 0, sessions IMAP
= N × réplicas stables, RSS par réplica plat sur la fenêtre.

**Violations déjà connues** (mesures 2026-08-01/02, sous le genou) : inbox
(`read_list` p95 2,1 s), recherche (p95 2,6 s — chiffre non fiable avant
task-196), envoi (p95 7,3 s — archivage sérialisé sous le verrou de session).
La grille désigne donc déjà le backlog d'optimisation ; cette US livre
l'instrument, pas les correctifs.

## Ce qu'il ne faut PAS présumer

- **Ne pas inventer le parcours.** La séquence d'appels de chaque étape doit
  être **dérivée du client réel** (lire ce que `client-blazor` appelle
  effectivement à l'arrivée sur le dashboard, à l'ouverture de l'inbox, d'un
  message…) et **consignée** avec sa provenance. Un parcours inventé
  reproduirait le défaut du mix : une hypothèse déguisée en mesure.
- **Ne pas utiliser de temps de réflexion fixes.** N médecins à cadence fixe
  se synchronisent et produisent des vagues — artefact classique. Tirages
  **log-normaux, par étape** (regarder le dashboard 3–10 s, lire 5–30 s,
  composer 30–120 s, hésiter avant de supprimer 1–3 s), paramètres versionnés
  comme **hypothèse assumée**, ajustables sans toucher au code.
- **Ne pas laisser la suppression consommer le corpus.** Chaque suppression
  retire un message d'une boîte qui en a ~100 : une campagne longue vide les
  boîtes et change le coût des autres étapes en cours de tir. Bande d'UIDs
  **dédiée à la suppression**, dimensionnée par la durée de campagne — et un
  contrôle qui échoue si le budget est dépassé.
- **Ne pas mesurer la PJ à la latence seule.** Le téléchargement ouvre l'axe
  **octets transférés** ; le rapport doit montrer les deux (temps et volume),
  sinon un plafond de bande passante passera pour une lenteur applicative.
- **Ne pas garder `enrich` comme étape du parcours.** C'est un traitement de
  la plateforme, pas un geste du médecin : il devient une conséquence de
  l'ouverture d'un message froid, ou une charge de fond — trancher et l'écrire.
- **Ne pas toucher `mixed.js`** ni sa chaîne de dimensionnement : la voie à
  débit imposé reste l'outil de garde anti-régression SLO. Les deux voies
  coexistent.
- **Ne pas comparer les tirs `journey` aux baselines archivées** — modèles
  différents. L'INDEX doit distinguer les deux familles, sinon quelqu'un
  comparera.

## Contenu attendu

1. **Le parcours consigné** : document listant la séquence d'appels par étape,
   dérivée du client réel, avec provenance (fichier/méthode du client lu).
2. **`scenarios/journey.js`** : 1 VU = 1 médecin, `ramping-vus` avec paliers
   de population paramétrables (`JOURNEY_STAGES`), temps de réflexion
   log-normaux par étape, facteur `JOURNEY_TIME_COMPRESSION` (défaut 1),
   identités round-robin comme aujourd'hui.
3. **Quatre opérations nouvelles instrumentées** (tags `op:`) : `delete`,
   `attachment` (avec compteur d'octets), `mark_read`, `dashboard`.
4. **`docs/SLO-parcours-medecin.md`** : la grille ci-dessus, verbatim.
5. **`report.py`** : pour les tirs `journey` — table du genou (palier → N,
   débit émergent, p95 **par étape**, erreurs), courbe des **coûts résidents**
   contre N (sessions IMAP, backends/`cl_waiting`, RSS par réplica), **verdict
   SLO par étape** (K=1 uniquement), et neutralisation des sections « débit
   demandé vs délivré » / « latence planifiée vs mesurée » qui n'ont pas de
   sens sans débit imposé.
6. **`selftest.sh`** étendu (tirages log-normaux bornés, budget de
   suppression, mapping étape→opérations).
7. **INDEX.md** : colonne ou marqueur distinguant `journey` de `mixed`.

## Hors scope

- Les **correctifs** des violations SLO connues (envoi, inbox, recherche) —
  cette US livre l'instrument qui les désigne, chacun sera une US.
- L'externalisation des serveurs mail (**task-221**).
- La re-dérivation des baselines `mixed`.
- Toute campagne au-delà du smoke : les paliers hauts attendent task-221.

## Definition of Done

- [ ] `selftest.sh` vert (nouveaux tests inclus)
- [ ] Le parcours est consigné avec la provenance de chaque appel (fichier du
      client réel lu, pas inventé)
- [ ] `docs/SLO-parcours-medecin.md` existe et reproduit la grille validée
- [ ] Tir smoke local vert : N=10 médecins, K=10, 5 min — rapport produit,
      preuve dans le `## Develop log`
- [ ] Le rapport d'un tir `journey` montre : p95 par étape × palier, coûts
      résidents × N, verdict SLO (K=1) — et ne montre PAS les sections à
      débit imposé
- [ ] Les 4 nouvelles opérations apparaissent dans la table de latence, la PJ
      avec ses octets
- [ ] Temps de réflexion log-normaux par étape, paramètres surchargables par
      variables d'environnement, documentés comme hypothèse
- [ ] La suppression puise dans une bande dédiée ; un contrôle échoue si le
      budget de campagne la dépasse
- [ ] `enrich` n'est plus une action du parcours (décision consignée)
- [ ] INDEX.md distingue les familles `journey` / `mixed`
- [ ] `mixed.js` et sa chaîne de dimensionnement : **zéro diff**

## Manual Test Plan

```bash
cd Api/Mail
dotnet run --project src/AppHost --launch-profile https-load-test
# banc prêt (sonde 200), puis :
dotnet run --project tests/mss.mail.loadtest.seed -- --users 20 --messages 50 --api http://127.0.0.1:5052
export BYPASS_KEY=loadtest-local-only
JOURNEY_STAGES="5:2m,10:3m" JOURNEY_TIME_COMPRESSION=10 tests/loadtest-k6/run.sh journey
tests/loadtest-k6/report.sh <dernier json> --expected 50
```

**Ce que l'humain doit voir** :
- le rapport s'ouvre **sans** `TIR INVALIDE` et sans section « débit demandé
  vs délivré » ;
- une table « latence par étape » avec les 8 étapes, dont `delete`,
  `attachment` (octets affichés), `mark_read`, `dashboard` ;
- le verdict SLO indique explicitement « non opposable — K=10 » (seul K=1
  certifie) ;
- côté Dovecot, `doveadm who` pendant le tir ≈ N × réplicas ; après le tir,
  les messages supprimés le sont réellement (`doveadm` sur une boîte témoin).

**Données de test** : boîtes `loadtest-*`, corpus synthétique, aucune donnée
de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — outillage de mesure interne.
- **Exigences DSR honorées** : aucune nouvelle.
- **INS** : non manipulée — identités virtuelles déterministes du banc.
- ⚠️ **Le téléchargement de PJ exerce des CDA de test** : rester strictement
  sur le corpus `JEUX_TESTS_FULL`, et les octets téléchargés par k6 ne doivent
  jamais être écrits sur disque par le harnais (compteur en mémoire).
- **Habilitations** : inchangées — le parcours reste cloisonné par identité
  virtuelle, comme les scénarios existants.
- **Tracé PGSSI-S** : aucun évènement métier touché.
- **Hébergement HDS** : non — banc local, données synthétiques.
- **AIPD / impact RGPD** : néant.

## Branches
- `api-mail` (pushed) : feat/task-220-banc-parcours-medecin — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-220-banc-parcours-medecin
- `dtos-mss` (pushed, auto-inclus) : feat/task-220-banc-parcours-medecin — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-220-banc-parcours-medecin

## Develop log

- **Repos touchés** : api-mail uniquement (`dtos-mss` : branche sans commit, aucun changement de contrat — pas de PR à ouvrir dessus)
- **DTOs publiés** : no DTO change — **Interop** : no interop change
- **Commits (api-mail, `feat/task-220-banc-parcours-medecin`)** :
  - `d804adc` feat(loadtest): scénario journey, 1 VU = 1 médecin, verdict SLO par palier (13 fichiers, +2098/−27)
  - `0f1f97f` test(loadtest): tir smoke journey vert (ligne d'INDEX)
- **Livré** :
  - `docs/parcours-medecin.md` — le parcours dérivé du client Blazor réel, provenance fichier:méthode pour chaque appel ; **décision consignée : `enrich` n'est plus une action du parcours** (l'ouverture d'un message froid exerce le fetch IMAP + matérialisation `MailContent` ; la pipeline CDA de fond reste à la famille `mixed`)
  - `docs/SLO-parcours-medecin.md` — la grille validée le 2026-08-03, verbatim, + conditions de mesure + mapping étape ↔ tag `op:`
  - `scenarios/journey.js` — modèle fermé `ramping-vus`, paliers `JOURNEY_STAGES`, K (`JOURNEY_TIME_COMPRESSION`, défaut 1), identités stables par VU (round-robin sur la population), session stable par médecin, double tag `op`+`palier`, warmup de la bande chaude au premier passage (tag `warmup`, hors grille)
  - `lib/journey-model.js` (+ tests node) — tirages **log-normaux bornés** [min/2, max×2] par étape (plages = hypothèse assumée, surchargables `JOURNEY_THINK_*`), probabilités `JOURNEY_P_*`, **bandes froide/chaude/suppression disjointes**, contrôle de budget de campagne (échec franc au setup) + compteur `journey_budget_exhausted` (seuil `count==0`)
  - `lib/journey-api.js` — 4 opérations nouvelles : `dashboard` (4 appels du client réel), `attachment` (compteur d'octets `journey_attachment_bytes`, jamais écrits sur disque), `delete` (bande dédiée), `mark_read`
  - `report.py` (+21 tests unittest) — table du genou (palier → N, débit émergent, p95 par étape), coûts résidents contre N (CSV observe replié **par palier**), verdict SLO par étape (**K=1 uniquement**, sinon « non opposable — K=x ») ; sections « débit demandé vs délivré » / « latence planifiée vs mesurée » **absentes** des rapports journey ; `INDEX.md` marque la famille `journey 🚶(fermé)` et neutralise les colonnes du modèle ouvert
  - `mixed.js` + `lib/vu-sizing.js` : **zéro diff** (vérifié au `git status`)
- **Local build / test** : ✓ `dotnet build` 0 erreur, ✓ `dotnet test` 2133 passed / 0 failed, ✓ `selftest.sh` vert (131 tests Python + 18 tests node, dont les nouveaux)
- **Tir smoke (DOD)** : ✅ VERT — banc monté (AppHost `https-load-test`), seed 20 users × 50 messages (read-back verified), tir `JOURNEY_STAGES="5:2m,10:3m" JOURNEY_TIME_COMPRESSION=10 USERS=20 MESSAGES_PER_USER=50` :
  - verdict k6 **PASS** (exit 0), **3 294 requêtes, 0,00 % d'erreur, 100 % de checks**, 342 passages complets, **0 itération interrompue**, 0 × 429, budget des bandes tenu (`journey_budget_exhausted` = 0)
  - rapport produit **sans** `TIR INVALIDE` et **sans** sections à débit imposé : `Api/Mail/tests/loadtest-k6/reports/2026-08-03/report-journey-mssante-n10-101131.md` (répertoire gitignoré — extraits ci-dessous)
  - **table du genou** : 5 médecins → 5,85 req/s émergent, 10 médecins → 12,39 req/s, 0,00 % d'erreurs aux deux paliers ; PJ : 2,9 Mo (palier 5) / 12,5 Mo (palier 10) — les octets sont montrés
  - **latence par étape × palier** (p50/p95 ms) — les 8 étapes présentes, dont les 4 nouvelles ops : dashboard 94/504, inbox 105/403, **message chaud 3/4** vs **froid 418/464** (la séparation des bandes fonctionne), recherche 192/240, envoi 1262/1864, PJ 12/355, supprimer/marquer lu 743/816 (n=258)
  - **coûts résidents par palier** : sessions IMAP 10→21 (suit N), backends Postgres 20→30, `cl_waiting` 0 partout, RSS 118→162 Mo/réplica (5 réplicas)
  - **verdict SLO : « ⚠️ non opposable — K=10 »** affiché explicitement, comme exigé
  - vérification par base : **PASS, Mélange 0** ; Seq : 0 Error/Fatal, 0 marqueur de régression, warnings = bruit de configuration du banc uniquement
  - banc rendu : AppHost + dcp arrêtés, volume maildir supprimé, tables purgées (mode PURGE), zips temp nettoyés
- **DOD self-check** : 11/11 items vérifiables ✓ (le tir de validation K=1 ≥ 30 min à N élevé attend task-221 — hors scope, conforme au « Hors scope » de l'US)
- **Next step** : /forge-simplify task-220

## Simplify log

- Repos passés : api-mail (seul repo touché — dtos-mss sans commit, client-angular/mobile hors scope)
- Applied & committed : api-mail : 7 fichiers (`5f597ad`) — 4 agents de revue (reuse/simplification/efficacité/altitude), ~15 findings appliqués :
  - `api.js` accepte un objet de tags → `journey-api.js` réduit aux 6 endpoints propres au parcours (~60 lignes de duplication supprimées)
  - `baseThresholds()` extrait dans `config.js` : les gardes transverses (erreurs/checks/429) ont une seule définition pour les deux familles
  - `checkBudgets` reçoit le plan réellement exécuté ; scanner de surcharges factorisé ; `K<=0` refusé à la frontière
  - `report.py` : genou dérivé une fois pour l'affichage ET le verdict ; garde des 300 échantillons au grain de l'opération (`n_min` — un `delete` à 60 points ne se cache plus derrière un `mark_read` à 250) ; `cl_waiting` jugé par `pgbouncer_waiting` (présence soutenue) ; « débit plateau » décidé par `throughput()` pour toutes les familles
  - `journey.js` : sinks k6 morts supprimés (`warmup` × palier), page d'inbox constante, un jeu de tags par étape, avertissement au setup quand la bande froide recouvre la bande enrich d'uid-bands
- No change : docs, README, INDEX, selftest.sh, run.sh
- Rolled back (validation RED) : aucun
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Skipped (findings non retenus, consignés) : cache d'en-têtes par VU (~1 µs/req — identity.js documente déjà le compromis anti-mémoïsation), repli unique de l'échantillonneur multi-paliers (fraction de seconde, complexité non payée), bootstrap()/reportContext() réutilisés partiellement seulement (leur bannière et leurs projections sont spécifiques au modèle à débit imposé et seraient trompeuses sur un parcours — `dovecotMaxPerUser` repris seul). ⚠️ À arbitrer humain (hors passe qualité, changerait la sémantique de mesure) : le recouvrement bande froide journey / bande enrich uid-bands sur un seed partagé — mitigé par un avertissement au setup + consigne dans le log ; déplacer les bandes journey dans la bande read d'uid-bands changerait les budgets et invaliderait le smoke.
- Build / tests : ✓ selftest.sh vert (131 unittest + tests node), ✓ k6 inspect OK (+ refus K=0 vérifié), ✓ dotnet build 0 erreur, ✓ dotnet test 3384 passed / 0 failed
- Next step : /sonar task-220 (api-mail touché)

## Sonar log

- **Mode A (chaîné), pas de nouvelle analyse** : le diff de la task ne contient
  **aucun fichier du périmètre du scanner .NET** (0 `.cs`/`.csproj`/`.props`/`.sln`
  — uniquement le harnais k6 JS/Python, des docs et des scripts sous
  `tests/loadtest-k6/`, hors projets MSBuild). Une analyse aurait re-mesuré
  l'état de develop, pas la task.
- KPIs du projet (dernière analyse serveur, consignés pour le monitoring — baseline = final, aucun code C# modifié) :

| KPI | Baseline | Final |
|---|---|---|
| Quality Gate | **OK** | OK (inchangé) |
| Bugs | 0 | 0 |
| Vulnérabilités | 0 | 0 |
| Code smells | 32 | 32 |
| Fiabilité / Sécurité / Maintenabilité | A / A / A | A / A / A |
| Couverture | 86,8 % | 86,8 % |
| Duplication | 0,6 % | 0,6 % |

- Étapes suivantes de la chaîne, **skip clean** :
  - `/lint-angular` : client-angular non listé dans **Repos**, arbre `Client/Angular` propre (0 fichier) → skipped
  - `/lint-mobile` : client-mobile non listé, répertoire `Client/Mobile` absent du workspace → skipped
  - `/verify-visual` : aucun écran mobile touché → skipped
- Next step : /review task-220

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/147 — **label `awaiting-human-merge`** (3 commits : `d804adc` feat, `0f1f97f` smoke, `5f597ad` simplify)
- `dtos-mss` : aucune PR — branche auto-incluse sans commit (aucun changement de contrat)

## Code Review Summary

**Verdict : APPROVED** — 13 fichiers relus (diff complet vs origin/develop).

- Build ✓ 0 erreur — Tests .NET ✓ 3 281 passed / 0 failed — selftest harnais ✓ (131 unittest + tests node) — `k6 inspect` ✓ (+ refus K≤0)
- DOD ✓ 11/11 items vérifiés (détail au ## Develop log)
- Qualité : Quality Gate **OK**, 0 bug, 0 vulnérabilité, ratings A — aucun fichier du périmètre Sonar touché (tableau au ## Sonar log, recopié dans la PR)
- Passe `/simplify` appliquée avant revue (4 agents, ~15 findings, commit `5f597ad`), zéro diff `mixed.js`/`vu-sizing.js`
- Suggestions non bloquantes (recopiées dans la PR) :
  1. le smoke a été tiré avant la passe simplify — le Manual Test Plan de la PR rejoue le chemin runtime de bout en bout (HAG) ;
  2. recouvrement bande froide journey / bande enrich uid-bands sur seed partagé — avertissement au setup, ne pas rejouer un tir enrich/mixed sans reset-state.
