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

## Branches

- `api-mail` (pushed) : `fix/task-222-open-enriched-mail-no-imap` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-222-open-enriched-mail-no-imap
- `dtos-mss` (pushed, auto-inclus) : `fix/task-222-open-enriched-mail-no-imap` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-222-open-enriched-mail-no-imap (aucun changement de contrat attendu — pas de PR si aucun commit)

## Develop log

- **Repos touchés** : `api-mail` uniquement. `dtos-mss` : aucun changement de
  contrat (branche créée par `/start`, restée vide → pas de PR, pas de publish
  NuGet). `client-angular` / `client-mobile` / `client-blazor` : hors scope
  (`**Single frontend**: true` — la US corrige un chemin d'accès backend, la
  réponse de l'API est inchangée).
- **DTOs publiés** : aucun changement DTO.
- **Interop publié** : aucun changement interop.
- **Commits** (`fix/task-222-open-enriched-mail-no-imap`) :
  - `458fc48` feat(telemetry): compter les sollicitations du serveur de messagerie par requête
  - `317a403` fix(mail): ouvrir un message déjà analysé ne repaye plus le trajet vers le serveur
- **Build / tests locaux** : ✓ `dotnet build` 0 erreur / 0 avertissement ;
  `dotnet test` **3 399 réussis, 0 échec**, 16 ignorés (tests d'intégration
  exigeant un IMAP vivant, ignorés d'avance). Aucun des 3 rouges pré-existants
  connus ne s'est manifesté.

### La cause, close

Le décompte manquant est instrumenté (`IMailServerSolicitationRecorder`,
`Scoped` = une instance par requête ; compteur
`mssante_mail_server_solicitations_total{command,operation}` + étiquette de
trace `mss.mail_server.solicitations`). Une session reprise du pool ne compte
pas : le décompte est une **borne inférieure exacte** du nombre
d'allers-retours, pas une estimation.

**Sur cette base, la cause est close — et ce n'était pas quatre allers-retours
de trop, c'était l'absence d'une écriture.**

`GetEmailContentAsync` **lisait** le stock (`ImapService.cs:1982`) sans jamais
**l'écrire**. Le corps ramené du serveur était assaini, renvoyé, puis **jeté**.
Le message ne devenait donc jamais « stocké », et chaque ouverture repayait le
trajet en entier — d'où le verrou de session pris **inconditionnellement**
(ex-ligne 1991) que la télémétrie fine avait vu, et d'où les trois faits du
constat, tous les trois expliqués par cette seule asymétrie :

| Fait du constat | Ce que l'absence d'écriture en retour explique |
|---|---|
| 440 ms (chaud) ≈ 442 ms (froid) | il n'y avait **pas** de chaud : chaque ouverture était froide |
| PJ du même message en 34 ms | `GetAttachmentAsync` **écrit** en retour (`UpdateAttachmentAsync`) — le contre-exemple était le témoin du correctif |
| aucune dérive avec la charge | un trajet payé une fois par ouverture est un coût **fixe**, pas de la contention |

Le harnais `journey` chauffait bien sa bande de relecture (`warmUpOwnMailbox`,
`scenarios/journey.js`) en appelant `getEmailContent` sur chaque UID chaud —
mais son commentaire « le GET contenu matérialise le MailContent » était
**faux** : rien ne le matérialisait. L'étape 3 mesurait donc du froid en croyant
mesurer du chaud. Le harnais n'est pas en cause (il décrivait le comportement
attendu), il était le premier à en souffrir.

**Le PO avait raison sur le fond** : ce n'était pas l'absence d'un cache,
c'était le chemin d'accès. Aucun cache n'a été ajouté — l'écriture en retour
**complète le stock que la voie rapide lisait déjà**.

### Ce qui a été écrit

`SaveMailContentAsync` (dépôt), la symétrie exacte de `UpdateAttachmentAsync`.
Chaque clause du contrat est un garde-fou, aucune n'est une commodité :

- **génération courante** (task-179) : la même identité `(dossier, uid,
  génération)` que celle que lit `GetMailAsync` ;
- **n'invente jamais de ligne `Mail`** → **cloisonnement par praticien**
  (point de vigilance de la US) : un contenu ne peut pas être greffé sur une
  boîte qui ne porte pas le message. La base est déjà par praticien ; cette
  clause interdit en plus d'y écrire pour un message absent ;
- **idempotente** : n'écrase pas le contenu de la chaîne d'enrichissement, plus
  riche (résumé, embedding, documents médicaux) ;
- **refuse un corps vide des deux côtés** : sinon elle fabriquerait l'état
  « présent mais inexploitable » que la lecture rejette — donc une boucle.

L'écriture en retour est **best-effort** : le médecin a son contenu en main, un
incident de stockage ne doit pas le lui retirer (il coûte seulement une
sollicitation de plus à l'ouverture suivante).

**Effet de bord assumé, et c'est une correction** : une ligne de contenu
entièrement vide (promotion d'en-tête interrompue) n'est plus servie — elle
affichait un **écran blanc définitivement**, puisque rien ne repassait jamais
dessus. Le résumé et les documents médicaux comptent autant que le corps : un
message dont toute la valeur clinique est dans son CDA a souvent un corps vide,
et le re-solliciter le renverrait **sans** ses documents médicaux (la voie
serveur ne les porte pas). Le contenu clinique n'est jamais échangé contre un
corps vide.

### Contenu périmé côté serveur — tranché

**Il ne peut pas l'être.** Dans IMAP (RFC 3501) le corps d'un message d'UID
donné est **immuable** au sein d'une génération de dossier : seuls les marqueurs
changent, et un contenu différent est un autre message, donc un autre UID. Si le
serveur renumérote (`UIDVALIDITY`), l'identité stockée n'est plus celle du
dossier courant : le filtre de génération de task-179 cesse de servir la ligne
périmée et le contenu est re-sollicité. L'écriture en retour **n'ouvre donc
aucune fenêtre de péremption** — le médecin ne peut pas voir un document
clinique périmé. Couvert par
`SaveMailContentAsync_WhenMailBelongsToAPreviousGeneration_WritesNothingAsync`.

### Vérification demandée sur `mssante_lock_hold_duration_seconds`

Vérifié : **l'émission est correcte, le défaut n'est pas dans le code.**
`ImapLockScope.DisposeAsync` enregistre bien la détention avec la famille
d'opération depuis task-214 (`MailProcessingMetrics.RecordLockHold(...,
_tags.Family, _tags.Lane)`), et `report.py` interroge bien
`sum by (le, operation) (rate(mssante_lock_hold_duration_seconds_bucket
{lock="imap_session"}[1m]))`. Le silence sur la fenêtre du tir est donc côté
**observation** (scrape / fenêtre `[1m]` face à un débit de parcours très bas :
3 111 itérations sur 35 min), pas côté instrumentation. Ce n'est **pas** la même
famille de défaut que task-214. Hors scope de ce correctif — à confirmer au
prochain tir, l'instrument étant en place.

### DOD — auto-contrôle

| Critère | État |
|---|---|
| Build passe (0 erreur) | ✓ |
| Tests passent (0 échec) | ✓ 3 399 / 0 |
| Décompte des sollicitations instrumenté + cause close dans le Develop log | ✓ (ci-dessus) |
| Tests unitaires du chemin corrigé (contenu présent / absent / présent mais invalide) | ✓ 6 tests, `ImapServiceTests` |
| Test d'intégration : ouverture d'un message déjà analysé ne sollicite plus le serveur (assertion sur le **nombre**) | ✓ 3 tests sur **vrai PostgreSQL**, `MailContentServedFromStoreIntegrationTests` — dont la preuve de bout en bout : 1re ouverture sollicite + stocke, **2e sollicite zéro fois** |
| Comportement en cas de contenu périmé tranché, écrit, couvert par un test | ✓ (immuabilité IMAP + garde de génération) |
| Aucune donnée de santé en clair dans les logs ajoutés | ✓ étiquettes littérales uniquement ; aucun corps, INS, chemin de dossier ni nom de PJ |
| Cloisonnement par praticien préservé (point de vigilance) | ✓ `SaveMailContentAsync_WhenNoMailRow_WritesNothingAsync` |
| **Tir `journey` K=1, étape 3 ≤ 100 ms p50 / ≤ 500 ms p95** | ⛔ **non exécuté — déféré au test humain (HAG)** |
| **Aucune régression sur les 7 autres étapes vs `report-journey-certif-n200-180029.md`** | ⛔ **non exécuté — déféré au test humain (HAG)** |

**Pourquoi les deux derniers ne sont pas faits, précisément** — deux blocages
matériels, aucun d'eux contournable par la forge :

1. **Le banc exige un nœud distant.** Le Manual Test Plan lui-même impose
   `MSS_LOADTEST_MAIL_HOST=<ip-noeud>` (serveurs de messagerie **hors** de la
   machine de mesure) et un tir de **35 minutes au rythme réel**
   (`JOURNEY_TIME_COMPRESSION=1`, seule forme qui rend un verdict opposable). La
   forge n'a pas ce nœud.
2. **Le rapport de référence est absent de cette machine.**
   `tests/loadtest-k6/reports/` est git-ignoré (seul `INDEX.md` est suivi) et ne
   contient localement que `2026-07-25`, `2026-07-26`, `2026-07-27`. Le
   répertoire `2026-08-03/` n'existe pas ; `INDEX.md` porte bien la ligne du tir
   (`report-journey-certif-n200-180029.md`, 200 VU, PASS) mais le fichier
   lui-même n'est pas là. La comparaison étape par étape exigée par le DOD est
   donc impossible ici.

La chaîne de causalité est en revanche **prouvée par test** sans le banc : le
test d'intégration établit que la seconde ouverture d'un message dont le contenu
a été stocké sollicite le serveur **zéro fois**, ce qui est l'énoncé même du DOD
(« assertion sur le nombre de sollicitations, pas sur un temps »). Le banc reste
nécessaire pour **chiffrer** le gain et confirmer l'absence de régression sur les
7 autres étapes — c'est le geste humain du HAG.

### Note pour le prochain tir `journey`

Le commentaire de `warmUpOwnMailbox` (`tests/loadtest-k6/scenarios/journey.js`)
affirme que le GET contenu matérialise le `MailContent`. C'était faux avant ce
correctif ; **c'est vrai depuis**. La chauffe du harnais fonctionne donc
désormais comme elle le prétendait, sans qu'il faille y toucher. En revanche
l'avertissement sur le partage de seed avec un tir `enrich`/`mixed` devient plus
large : la bande **chaude** matérialise elle aussi du `MailContent` maintenant.
Signalé, non modifié — l'outillage de mesure est task-224.

- **Étape suivante** : `/forge-simplify task-222`

## Simplify log

- **Repos éligibles touchés** : `api-mail` seul. `dtos-mss` : porteur de contrat
  → jamais simplifié (et sa branche est vide de toute façon). Aucun frontend
  touché.
- **Commit** : `ee095f1` refactor(mail): passe qualité sur le code frais
- **Re-validation** : build 0 erreur / 0 avertissement ; **3 399 tests verts,
  0 échec** (filet anti-régression — la passe qualité ne change pas le
  comportement). Aucun rollback.

### Ce qui a été simplifié

| Axe | Fichier | Avant → après |
|---|---|---|
| Simplification | `MailServerSolicitationRecorder` | `lock` + `List<string>` + champ `_gate` → `ConcurrentQueue<string>`. Le verrou manuel et le champ de garde disparaissent, trois membres deviennent des expressions, la garantie de ne perdre aucun incrément est la même. |
| Réutilisation + efficacité | `MailRepository.SaveMailContentAsync` | l'existence d'un contenu se lisait dans une **seconde** requête ; elle se lit désormais dans la **même** que le message, via la projection légère `Select(m => new { m.Id, ContentCount = m.MailContents.Count })` — l'idiome déjà employé par `TryResolveExistingMailAsync` juste au-dessus dans ce fichier. **2 requêtes au lieu de 3** sur un chemin appelé à chaque ouverture froide. |

### Ce qui a été examiné et laissé tel quel

- **Les 6 appels `Record(MailServerCommands.X, GetEmailContentOperation)`** dans
  `ImapService` : un helper privé économiserait ~20 caractères par ligne mais
  masquerait la famille d'opération, qui est précisément l'information utile et
  ce sur quoi on grep. L'explicite gagne — pas de churn.
- **Le découpage `GetEmailContentAsync` / `…CoreAsync`** : le `try/finally` du
  premier existe pour n'apposer l'étiquette de trace qu'en **un seul point**
  malgré les huit retours du chemin. Le fusionner rendrait les huit retours
  responsables du marquage — l'inverse d'une simplification.
- **`HasDisplayableContent`** : quatre conditions, chacune nommée dans la
  documentation par ce qu'elle protège. Rien à factoriser sans perdre le
  pourquoi.
- **Étape suivante** : `/sonar task-222` (api-mail touché).

## Lint / verify-visual log

Les trois étapes frontend **skippent proprement** : `**Repos**: api-mail` et
`**Single frontend**: true` — la US corrige un chemin d'accès backend et ne
change pas la réponse de l'API, donc aucun frontend n'a été touché.

| Étape | Verdict | Constat |
|---|---|---|
| `/lint-angular` | **skip** | `Client/Angular` est sur `feature/nova-rewriting-mss` avec deux fichiers modifiés non commités (`front/apps/mss/src/environments/environment.ts`, `front/apps/weda2/src/environments/environment.ts`). **Ce sont des travaux en cours de l'humain, pas de task-222** : la forge n'a écrit aucune ligne d'Angular sur cette task. Lancer la passe lint reviendrait à retoucher le WIP de l'humain — on s'abstient et on le dit, plutôt que de laisser le tronc sale déclencher un lint qui ne nous appartient pas. |
| `/lint-mobile` | **skip** | `Client/Mobile` sur `develop`, arbre propre, aucun diff vs `origin/develop`. `client-mobile` n'est pas listé dans `**Repos**:` — `/start` n'y a donc créé aucune branche, conformément au filet de sécurité désactivé. |
| `/verify-visual` | **skip** | Aucun écran mobile touché : rien à capturer, aucune référence Stitch à apparier. |

## Sonar log

Mode A (chaîné), 2 itérations, projet `healthplatform`, branche
`fix/task-222-open-enriched-mail-no-imap`.

### KPIs qualité — baseline → final

| Métrique | Baseline (avant task-222) | Final | Cible LT |
|---|---|---|---|
| Bugs | 1 | **1** | 0 |
| Vulnerabilities | 0 | **0** | 0 ✓ |
| Security Hotspots (à revoir) | 1 | **1** | 0 |
| Code Smells | 18 | **18** | — |
| Coverage | 86,9 % | **87,0 %** | ≥ 95 % |
| Duplication | 0,5 % | **0,5 %** | — |
| Reliability rating | C | **C** | A |
| Security rating | A | **A** | A ✓ |
| Maintainability rating | A | **A** | A ✓ |
| ncloc | 41 266 | 41 478 | — |
| **Quality Gate** | ERROR | **ERROR** | OK |

### Zero-new-debt : tenu

| Itération | Finding new-code attribuable à task-222 | Action |
|---|---|---|
| 1 | `csharpsquid:S125` (code commenté) — `IMailRepository.cs:66` | corrigé, `1c2b24c` |
| 2 | **aucun** | — |

Le finding était un **faux positif de forme** : le bloc de commentaire
documentant le contrat de `SaveMailContentAsync` cite `(folderPath, uid)`,
`MailContent`, `GetMailAsync` et termine ses puces par des points-virgules —
Sonar l'a lu comme du code mis en commentaire. Converti en commentaire de
documentation XML (`<summary>` / `<remarks>` / `<returns>` avec une `<list>`),
ce qui est de toute façon la forme attendue sur un membre d'interface :
`MailRepository.SaveMailContentAsync` y renvoyait déjà par `<see cref>`.

**Après correction : zéro finding new-code sur le code de task-222.**

### Le Quality Gate est ERROR, et ce n'est pas task-222

Il faut le dire nettement plutôt que de laisser la couleur parler : le QG est en
`ERROR` sur `new_violations = 18 > 0` et
`new_security_hotspots_reviewed = 83,3 % < 100 %`, et **aucune de ces
18 violations n'appartient à task-222**. Provenance vérifiée une par une :

| Origine | Fichiers | Count |
|---|---|---|
| **task-220** (harnais de mesure `journey`) | `tests/loadtest-k6/report.py`, `scenarios/journey.js`, `lib/journey-model.js` | 16 (dont l'unique `BUG`, `python:S1244`, et l'unique hotspot `javascript:S2245`) |
| **antérieur à la forge** | `src/Infrastructure/Repository/BaseRepository.cs:68`, `src/Application/Services/Interfaces/IIheXdmProcessingService.cs:9` (`csharpsquid:S103`) | 2 |
| **task-222** | — | **0** |

C'est exactement le piège déjà connu : la *new-code period* du projet est une
baseline large, elle englobe donc des tasks **déjà mergées**. Un QG rouge n'y
signifie pas « cette task a introduit de la dette ». Les 9 `S3776` (complexité
cognitive) relèvent par ailleurs de `/sonar-s3776`, hors chaîne autonome par
construction (1 méthode = 1 PR), et les findings Python/JS du harnais de charge
ne sont pas du code produit.

**Aucun de ces 18 n'a été touché** : les corriger serait sortir du scope de la
US et gonfler une PR de correctif de performance avec du nettoyage de harnais.
Best-effort assumé, findings restants acceptés — et nommés, pas passés sous
silence.

### Note pour `conventions/csharp.md`

Entrée `S125` ajoutée : sur un **membre d'interface**, documenter le contrat en
commentaire `//` multi-ligne se fait signaler dès que le texte cite des
identifiants et ponctue en `;`. Écrire d'emblée un commentaire de documentation
XML — c'est la forme attendue à cet endroit, et elle est visible à l'appel.

- **Étape suivante** : `/review task-222`
