# todo-task-222.md — Ouvrir un message déjà analysé ne doit plus repayer le trajet vers le serveur de messagerie

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. L'instrument qui désigne ce goulet et qui validera le
correctif est livré (**task-220**, scénario `journey` + grille SLO) et le banc
qui rend la mesure honnête l'est aussi (**task-221**). Rien à attendre.
**Priorité**: **2** — c'est **le** goulet que la première campagne de
certification a désigné, sur le geste que le médecin répète le plus après
l'ouverture de sa boîte. Rien n'est cassé : c'est lent, tout le temps.

## Objective

Qu'ouvrir un message dont le contenu est **déjà analysé et stocké** coûte au
médecin le temps d'une lecture en base, et non celui d'un aller-retour vers le
serveur de messagerie.

## Le constat — mesuré, avec son contre-exemple dans la même campagne

Campagne de certification du **2026-08-03** (rapport
`reports/2026-08-03/report-journey-certif-n200-180029.md`), 200 médecins au
rythme réel, 6 343 ouvertures de message mesurées :

| Geste du médecin | p50 mesuré | Cible SLO | |
|---|---|---|---|
| Ouvrir un message **déjà analysé** (servi base) | **440 ms** | 100 ms | ❌ |
| Ouvrir un message **jamais ouvert** (le serveur de messagerie est sollicité) | 442 ms | 800 ms | ✅ |
| **Télécharger la pièce jointe du même message déjà analysé** | **34 ms** | 500 ms | ✅ |

Trois faits, et c'est leur conjonction qui fait l'US :

1. **Ouvrir un message déjà analysé coûte exactement le même temps que d'aller
   le chercher sur le serveur de messagerie** (440 vs 442 ms). L'analyse
   préalable n'apporte donc **rien** au médecin sur ce geste — alors que c'est
   toute sa raison d'être.
2. **Le contre-exemple est dans la même campagne** : la pièce jointe du même
   message, ~124 Ko, est servie en **34 ms**. Servir depuis le stock local sans
   solliciter le serveur de messagerie est donc démontré possible sur cette
   installation — ce n'est pas une limite physique.
3. **Ce coût ne dépend pas de la charge** : 439 ms à 50 médecins, 443 à 100,
   440 à 200. Aucune dérive. Ce n'est pas de la saturation, c'est un **coût
   fixe payé à chaque ouverture**.

Ordre de grandeur du gain pour le médecin : ~400 ms rendues sur chaque
ouverture de message, soit le geste le plus fréquent de sa journée après le
rafraîchissement de sa boîte.

## Ce qu'il ne faut PAS présumer

- **Ne pas repartir de zéro sur la cause : elle est déjà établie aux trois
  quarts.** L'analyse de télémétrie fine de la campagne (section « Télémétrie
  fine » du rapport `report-journey-certif-n200-180029.md`) a établi, sur la
  trace `4d911c462694fab4d7454de2453bb13f` (ouverture d'un message chaud,
  439 ms) :
  - **19 ms** pour résoudre le praticien et sa base — le coût n'est pas là ;
  - **420 ms passées à l'intérieur du verrou de session IMAP**, pris
    **inconditionnellement** par `GetEmailContentAsync` (`ImapService.cs:1991`),
    avec **`WaitTimeMs=0`** — donc **du travail, pas une file d'attente**
    (contrairement au diagnostic de task-211 sur un autre chemin) ;
  - le p95 **serveur** de la route (497 ms) **égale** le p95 client (494 ms) :
    le temps est intégralement dans l'application, aucune file hors d'elle.
- **Ce qui reste à établir, et qui exige une instrumentation** : le **décompte
  des sollicitations du serveur de messagerie par requête**. 420 ms est
  *compatible* avec quatre allers-retours à 95 ms — ce n'est pas une preuve, et
  les commandes IMAP ne sont pas instrumentées à ce grain. **Cette
  instrumentation fait partie de la US** : sans elle, on ne pourra ni prouver la
  cause, ni démontrer que le correctif l'a supprimée (le test d'intégration du
  DOD en dépend). À noter au passage : `mssante_lock_hold_duration_seconds` par
  `operation` n'a rien rendu sur la fenêtre du tir alors que la métrique existe
  — même famille de défaut que celui corrigé par task-214 ailleurs, à vérifier.
- **Ne pas « ajouter un cache » devant le problème.** Le contenu est déjà
  stocké : s'il faut un cache pour aller le chercher vite, c'est le chemin
  d'accès qui est en cause, pas l'absence de cache. Un cache masquerait le
  coût au lieu de le supprimer, et ferait porter au médecin le risque d'un
  contenu périmé sur un document de santé.
- **Ne pas dégrader l'ouverture d'un message jamais ouvert.** Elle tient
  largement sa cible (442 ms pour 800 ms) : c'est un acquis à ne pas échanger.
  Le DOD l'exige explicitement.
- **Ne pas traiter au passage la suppression / le marquage comme lu** (807 ms
  pour une cible de 200 ms). C'est très probablement la même famille de coût,
  mais ces gestes **modifient** la boîte et doivent donc légitimement
  solliciter le serveur de messagerie au moins une fois : leur plancher n'est
  pas le même et leur arbitrage est distinct. Ils seront **re-mesurés après**
  ce correctif, et feront l'objet d'une US propre s'ils ne suivent pas.
- **Ne pas conclure sur un tir de découverte.** Seul un tir au rythme réel
  (`JOURNEY_TIME_COMPRESSION=1`) certifie une étape ; le rapport refuse de
  lui-même le verdict au-delà.

## Contenu attendu

1. **L'instrumentation qui manque** : le décompte des sollicitations du serveur
   de messagerie par requête, sans lequel la cause reste compatible mais non
   prouvée — et sans lequel le correctif ne sera pas démontrable.
2. **La cause close et consignée** sur cette base (le reste est déjà établi :
   voir « Ne pas présumer » ci-dessus).
3. **Le correctif**, à l'altitude que la cause désigne.
4. **La contre-épreuve au banc** : tir `journey` K=1, palier de population
   identique à celui du 2026-08-03, comparé étape par étape au rapport de
   référence — gain sur l'étape 3, **aucune régression** sur les 7 autres.
5. **Le cas du message analysé mais dont le contenu a changé côté serveur**
   doit rester correct : ce qu'on affiche au médecin ne doit jamais être un
   contenu clinique périmé. À trancher et à écrire.

## Hors scope

- La suppression / le marquage comme lu (étape 8) — re-mesurés après, US propre.
- L'envoi (étape 6, 1 321 ms pour 1 000 ms) — dépassement plus serré, et
  **task-216** (retrait de la voie d'écriture) va déjà déplacer ce chemin.
- Toute modification de la grille SLO : elle est validée par l'humain, c'est le
  produit qui s'y conforme, pas l'inverse.
- L'outillage de mesure (**task-224**).

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] Le **décompte des sollicitations du serveur de messagerie par requête** est
      instrumenté, et la cause des ~440 ms **close** sur cette base dans le
      `## Develop log` (l'analyse de la campagne en a déjà établi les trois quarts)
- [ ] Tests unitaires du chemin d'ouverture corrigé (≥ 1 test par branche :
      contenu présent en base, contenu absent, contenu présent mais invalide)
- [ ] Test d'intégration prouvant qu'une ouverture de message **déjà analysé**
      ne sollicite plus le serveur de messagerie (assertion sur le nombre de
      sollicitations, pas sur un temps)
- [ ] Tir `journey` **K=1** au banc, même palier que la campagne du 2026-08-03 :
      **étape 3 « ouvrir un message enrichi » ≤ 100 ms de p50 et ≤ 500 ms de p95**
- [ ] **Aucune régression** sur les 7 autres étapes du parcours face au rapport
      `report-journey-certif-n200-180029.md` (marge de 20 %), et en particulier
      l'étape 4 (message jamais ouvert) reste sous sa cible de 800 ms
- [ ] Le comportement en cas de contenu périmé côté serveur est tranché, écrit,
      et couvert par un test
- [ ] Aucune donnée de santé en clair dans les logs ajoutés (contenu CDA, INS)

## Manual Test Plan

```bash
# 1. Banc distant (serveurs de messagerie hors de la machine de mesure)
cd Api/Mail
MSS_LOADTEST_MAIL_HOST=<ip-noeud> dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 150 \
  --api http://127.0.0.1:5052 --mail-host <ip-noeud> --latency 95

# 2. Purge des contenus analysés, puis contre-épreuve au rythme réel
YES=1 tests/loadtest-k6/reset-state.sh
export BYPASS_KEY=loadtest-local-only MSS_LOADTEST_MAIL_HOST=<ip-noeud>
LATENCY_MS=95 USERS=200 MESSAGES_PER_USER=150 \
  JOURNEY_STAGES="200:35m" JOURNEY_TIME_COMPRESSION=1 \
  tests/loadtest-k6/run.sh journey
tests/loadtest-k6/report.sh <dernier json> --expected 0
```

**Ce que l'humain doit voir** :
- le rapport annonce un **verdict opposable** (K=1) et non « non opposable » ;
- l'étape **3 « Ouvrir un message enrichi (servi base) » passe au vert** ;
- l'étape **4 « message froid » reste verte** — on n'a pas déshabillé l'une
  pour habiller l'autre ;
- les étapes 1, 2, 5, 7 restent dans leurs cibles ;
- à l'écran, en ouvrant un message déjà consulté dans le client : l'affichage
  est **immédiat**, sans temps d'attente perceptible.

**Données de test** : boîtes `loadtest-*`, corpus synthétique `JEUX_TESTS_FULL`,
aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — la US améliore le temps de restitution d'un
  document déjà reçu et analysé, elle ne modifie aucun contrat d'interopérabilité.
- **Exigences DSR honorées** : aucune nouvelle. Aucune exigence existante n'est
  relâchée : le contenu affiché reste le document reçu, inchangé.
- **INS** : non manipulée par cette US — le chemin corrigé restitue un contenu
  déjà rattaché ; le rattachement lui-même n'est pas touché.
- **Authentification PS** : inchangée (PSC / e-CPS, niveau eIDAS substantiel au
  moins) — la US ne touche ni l'authentification ni le contrôle d'accès.
- **Habilitations** : inchangées. ⚠️ **Point de vigilance explicite** : si le
  correctif introduit une lecture directe du stock local, le **cloisonnement par
  praticien** doit être préservé — un médecin ne doit jamais pouvoir obtenir le
  contenu d'un message d'une autre boîte. À couvrir par un test.
- **Interop CI-SIS** : CDA r2 (volets CR de biologie / lettre de liaison selon
  le document reçu) — **lecture seule**, aucun document produit ni transformé.
- **Tracé PGSSI-S** : évènement « consultation d'un document de santé par un PS »
  déjà journalisé — **doit le rester à l'identique** après correctif (le DOD
  l'exige indirectement par la non-régression). Durée de conservation inchangée.
- **Consentement patient** : non applicable — consultation par le PS
  destinataire du message, dans le cadre de la prise en charge.
- **Référentiels métier** : aucun nouveau (les codes portés par les documents
  reçus ne sont pas retouchés).
- **Hébergement HDS** : oui en production — le contenu lu est une DSCP. Le banc
  de mesure reste local et synthétique.
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement, aucune nouvelle
  donnée collectée, aucune durée de conservation modifiée.
