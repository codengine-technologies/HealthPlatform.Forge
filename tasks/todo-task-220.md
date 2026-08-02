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
