# todo-task-288.md — Fiabiliser la vérification de révocation des certificats MSSanté (OCSP et CRL)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009

## Objective

La vérification de révocation OCSP des certificats serveur MSSanté est
**structurellement hors service**. Le point d'accès de l'IGC-Santé qui publie le
certificat d'autorité intermédiaire répond `403 Forbidden` à chaque tentative, et
l'application le re-sollicite à **chaque poignée de main TLS** — donc à chaque
ouverture de dossier et à chaque envoi.

Le service ne s'en rend pas compte parce que le repli CRL fonctionne :

```
[ValidateRevocation] OCSP validation failed, falling back to CRL. Errors: Error processing the AIA extension.
[ValidateRevocation] Server certificate is valid (CRL fallback check passed).
```

Rien n'est cassé fonctionnellement aujourd'hui. Mais **le dernier filet est déjà
en service**, et la posture retenue en arbitrage (grâce de 4 h sur cache périmé
puis fail-close) suppose que la CRL soit un secours occasionnel, pas le mode
nominal. Le jour où la CRL est indisponible à son tour — même hébergeur, même
exposition — les connexions IMAP et SMTP sont refusées sous 4 h.

Cette US remet OCSP en service, cesse de maltraiter le point d'accès de l'ANS,
et applique le même durcissement au chemin CRL pour qu'il redevienne un vrai
secours.

## Constat (mesuré le 2026-09-01)

**Ce n'est ni nouveau, ni lié à la conteneurisation.** La même erreur est
présente en mode projet Windows (`MachineName: WEDA-0138`, chemins
`D:\TechWatch\…`) à **15:50**, soit 3 h 40 avant le premier démarrage en
conteneur (`MachineName: 49c0f3327755`, 19:29). Elle n'avait simplement jamais
été regardée.

**Le point d'accès limite le débit par IP source, très agressivement.** Testé à
la main sur `http://igc-sante.esante.gouv.fr/AC/ACI-EL-ORG.cer` :

| Essai | Résultat |
|---|---|
| 1ʳᵉ série, sans en-tête `User-Agent` | **200**, 1856 octets |
| 1ʳᵉ série, `User-Agent` de navigateur | **200** |
| 2ᵉ série une minute plus tard, **toutes** variantes | **403** |

Ce n'est donc **pas** un filtrage sur `User-Agent` — les combinaisons qui
passaient échouent au second passage. Quelques requêtes suffisent à déclencher le
blocage, qui persiste ensuite.

**L'application entretient elle-même son blocage.** Trois défauts se composent :

1. **Aucun cache négatif.** Le cache (mémoire puis Redis partagé, 24 h) n'est
   alimenté que par les **succès**. Un échec n'est pas mémorisé, donc la
   poignée de main suivante retente — et maintient le blocage.
2. **Aucun backoff.** Deux tentatives immédiates, puis on recommence au
   handshake suivant. Relevé dans les journaux : 20:00:20, 20:03:24, 20:03:54,
   20:08:00, 20:09:01, 20:09:39.
3. **Aucune sérialisation.** Rien ne garantit qu'un seul téléchargement soit en
   vol pour une même URL : N poignées de main simultanées font N téléchargements
   du même octet.

**Le volume nominal est pourtant dérisoire.** Le certificat d'AC pèse
1856 octets, il est mis en cache 24 h, et il change tous les plusieurs
années. Le régime normal est **un téléchargement par jour et par autorité**.
Tout le problème vient de ce que, l'échec n'étant jamais mémorisé, ce régime
n'est jamais atteint.

**Le chemin CRL a exactement la même forme** — client HTTP nommé non
enregistré, réessai borné, mise en cache des seuls succès. Il ne tient que
parce qu'il réussit encore, et qu'un succès lui vaut 24 h de cache.

**Point d'attache manquant.** Les clients nommés `"OcspClient"` et `"CrlClient"`
ne sont **jamais enregistrés** — `CreateClient` rend un client par défaut, sans
politique de résilience ni délai propre. C'est là que doit se poser le
durcissement.

## Règles métier

1. **La révocation reste vérifiée.** Cette US ne relâche aucun contrôle : elle
   restaure le chemin nominal (OCSP) et consolide le repli (CRL). La posture
   arbitrée — grâce de 4 h sur cache périmé, puis fail-close ; certificat révoqué
   refusé immédiatement et sans grâce — est **inchangée**.

2. **Un échec de téléchargement est mémorisé.** Une indisponibilité du point
   d'accès n'est pas réessayée à la poignée de main suivante. La durée de
   mémorisation est courte devant le cache de succès, pour qu'un rétablissement
   soit repris rapidement.

3. **Les réessais sont espacés.** Après un échec, les tentatives suivantes sont
   progressivement espacées plutôt que répétées à chaque handshake. L'objectif
   est explicite : **cesser d'entretenir le blocage** et laisser la limitation de
   débit se lever.

4. **Un seul téléchargement en vol par ressource.** Des poignées de main
   simultanées qui ont besoin de la même ressource attendent le même
   téléchargement. En régime établi, l'application ne sollicite l'ANS qu'**une
   fois par jour et par autorité**.

5. **Le certificat d'AC intermédiaire est livré avec l'application.** Il amorce
   le cache au démarrage, sans aucun accès réseau. Démarrage à froid immédiat et
   indépendant de la disponibilité de l'ANS.

6. **La graine ne remplace pas le téléchargement.** Toute autorité inconnue de
   la graine reste résolue en ligne, selon les règles 2 à 4. Un oubli de mise à
   jour de la graine dégrade donc les performances, **jamais la correction** :
   c'est ce qui rend la règle 5 sans risque.

7. **Le même traitement s'applique aux deux chemins**, OCSP et CRL. Le repli
   doit être aussi robuste que le chemin nominal, puisqu'il est le dernier
   rempart avant le fail-close.

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] Les clients HTTP de révocation sont enregistrés explicitement, avec délai
      et politique de résilience propres
- [ ] Test : deux échecs consécutifs ne produisent **pas** deux salves de
      téléchargement — le second est servi par la mémorisation de l'échec
      (règle 2)
- [ ] Test : après un échec, les tentatives sont espacées et non répétées à
      chaque sollicitation (règle 3)
- [ ] Test : N demandes concurrentes sur la même ressource déclenchent **un
      seul** téléchargement (règle 4)
- [ ] Test : au démarrage, la vérification de révocation fonctionne **sans
      aucun accès réseau** vers l'ANS, grâce à la graine (règle 5)
- [ ] Test : une autorité absente de la graine est bien résolue en ligne
      (règle 6 — c'est le test qui prouve que la graine n'a pas introduit
      d'angle mort)
- [ ] Test : un certificat révoqué reste refusé immédiatement, sans grâce
      (non-régression de la posture arbitrée, règle 1)
- [ ] Test : la grâce de 4 h puis le fail-close sont inchangés
      (non-régression, règle 1)
- [ ] Le durcissement couvre les deux chemins, OCSP **et** CRL (règle 7)
- [ ] La provenance et la date de la graine sont documentées, ainsi que la
      procédure de mise à jour à la rotation de l'autorité
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. **Démarrage à froid, sans réseau vers l'ANS.** Vider le cache Redis
   (`docker exec … redis-cli FLUSHALL`), démarrer le backend, puis se connecter
   et ouvrir la boîte de réception. **Attendu** : la vérification de révocation
   aboutit, et **aucune** requête vers `igc-sante.esante.gouv.fr` n'apparaît dans
   les journaux. C'est le test central de la US.
2. **Régime établi.** Naviguer une dizaine de minutes (dossiers, ouverture de
   messages, un envoi). **Attendu** : dans Seq, filtrer sur
   `SourceContext like '%OcspValidationService%'` — aucune erreur, et au plus un
   téléchargement par autorité.
3. **Point d'accès indisponible.** Simuler l'indisponibilité (règle de pare-feu
   sortante, ou pointage sur une URL qui renvoie 403). Ouvrir la boîte de
   réception plusieurs fois de suite. **Attendu** : le service **ne repart pas**
   en téléchargement à chaque sollicitation ; les tentatives s'espacent ; la
   connexion aboutit toujours via le cache ou la CRL.
4. **Concurrence.** Cache vidé, ouvrir simultanément plusieurs onglets qui
   chargent la boîte de réception. **Attendu** : un seul téléchargement par
   ressource dans les journaux, pas un par onglet.
5. **Non-régression de la posture.** Vérifier qu'un certificat révoqué est
   toujours refusé immédiatement, et que le comportement au-delà de la fenêtre
   de grâce de 4 h est inchangé.
6. **Rotation de l'autorité.** Renommer la graine pour simuler une autorité
   inconnue. **Attendu** : la résolution en ligne prend le relais (règle 6),
   sans échec fonctionnel.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors périmètre fonctionnel DSR — correctif de robustesse sur
  un socle MSSanté déjà référencé
- **Exigences DSR honorées** : aucune exigence DSR fonctionnelle nouvelle. La US
  restaure le respect effectif de la **PGSSI-S § cryptographie et validation des
  certificats** et du Référentiel socle MSSanté #2 §2.1.1.2.3 (vérification du
  certificat serveur présenté par l'Opérateur, certificat IGC Santé). **Le
  rattachement DSR précis est à confirmer avec le référent Ségur** — je ne cite
  pas de code d'exigence que je n'ai pas vérifié.
- **INS** : non applicable — la validation de certificat ne manipule aucune
  donnée patient.
- **Authentification PS** : PSC / e-CPS, inchangé. La US porte sur
  l'authentification **du serveur MSSanté**, pas sur celle du praticien.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — aucun échange métier.
- **Tracé PGSSI-S** : à journaliser — échec de résolution d'une autorité, entrée
  en réessai espacé, usage de la graine au démarrage, entrée en fenêtre de grâce,
  fail-close. Ces évènements sont ceux que `todo-task-287` doit rendre
  mesurables ; les deux US se complètent sans se recouvrir (287 **compte**,
  288 **corrige**).
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — l'API héberge des DSCP. La US ne crée aucun
  nouveau flux de données de santé ; la graine est un certificat d'autorité
  publique.
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle traitée.
- **Sécurité** : point de vigilance central — **aucun assouplissement du
  contrôle de révocation n'est acceptable au prétexte de la robustesse.** Un
  échec de résolution ne doit jamais devenir un succès implicite. La graine ne
  fait qu'éviter un téléchargement ; elle ne dispense d'aucune vérification, et
  un certificat révoqué reste refusé sans grâce.

## Note — origine du constat

Défaut relevé le 2026-09-01 en analysant les journaux Seq après le passage en
profil conteneur. L'humain l'a signalé comme « une erreur jamais vue en Aspire » ;
l'instruction a montré qu'elle était **présente dès le mode projet le même jour**,
et probablement bien avant. C'est exactement le type d'angle mort que
`todo-task-287` doit supprimer : un défaut réglementaire silencieux, découvert
par lecture de journaux et non par un signal.

## Timings

*(généré par `tools/timing/report.sh --task task-288 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 41 s | — | — | — | — |
| /develop | ok | 33 min 11 s | 6 (1 min 43 s) | 3 (3 min 11 s) | — | api-mail 6B/3T |
| /sonar | ok | 22 min 44 s | 2 (34 s) | 11 (9 min 00 s) | 2 (3 min 43 s) | 2 itération(s), api-mail 2B/11T |
| /lint-angular | skipped | 2.1 s | — | — | — | client-angular non touche (Repos: api-mail) |
| /lint-mobile | skipped | 2.0 s | — | — | — | client-mobile non touche (Repos: api-mail) |
| /verify-visual | skipped | 1.8 s | — | — | — | aucun ecran mobile touche (Repos: api-mail) |
| /review | ok | 20 min 23 s | 1 (11 s) | 2 (2 min 59 s) | — | api-mail 1B/2T |
| /tech-writer | ok | 2 min 38 s | — | — | — | — |
| **Total cycle** | | **1 h 19 min** | **9 (2 min 30 s)** | **16 (15 min 10 s)** | **2 (3 min 43 s)** | |

## Branches

- `api-mail` (pushed) : `fix/task-288-ocsp-crl-hardening` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-288-ocsp-crl-hardening
- `dtos-mss` (pushed, auto-inclus) : `fix/task-288-ocsp-crl-hardening` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-288-ocsp-crl-hardening

Base : `origin/develop` @ `b386a1c` (inclut `b3e7938` — politique TLS/suites de
chiffrement MSSanté #2 — et le profil conteneur `MSS_API_IN_CONTAINER`). Le
premier `/start 288` du 2026-09-01 avait été refusé faute de cette base :
`questions/task-288.md`.

## Develop log

**Repos touchés** : `api-mail` uniquement. `dtos-mss` (branche auto-créée) est
resté vide — la US ne change aucun contrat, elle durcit un chemin interne.

### Ce qui a été fait

| Règle | Mécanisme | Où |
|---|---|---|
| 2 — un échec est mémorisé | fenêtre de refus par point d'accès, ouverte à l'échec | `RevocationDownloadCoordinator` |
| 3 — les réessais s'espacent | doublement 30 s → 60 s → 120 s…, plafond 30 min | idem |
| 4 — un seul téléchargement en vol | `Lazy<Task>` en `ExecutionAndPublication`, clé de ressource | idem |
| 5 — graine livrée avec l'app | 4 certificats IGC-Santé en ressources embarquées, indexés par **sujet DER** | `EmbeddedIssuerCertificateSeed` |
| 6 — autorité hors graine | résolution AIA en ligne inchangée, sous la discipline du coordinateur | `OcspValidationService` |
| 7 — les deux chemins | le coordinateur enveloppe OCSP **et** CRL | `CrlValidationService` |
| DOD — clients HTTP explicites | délai court + gestionnaire de résilience **sans réessai** | `RevocationHttpClientExtensions` |

### Trois constats d'instruction, au-delà de l'énoncé

1. **Les clients nommés *étaient* enregistrés** — `AddHttpClient("OcspClient")`
   et `AddHttpClient("CrlClient")` existent depuis task-057. L'énoncé les disait
   « jamais enregistrés » ; ce qui manquait était la **politique**. Et la
   situation réelle était pire que l'absence : `ConfigureHttpClientDefaults`
   (`AddServiceDefaults`) leur imposait `TotalRequestTimeout` et
   `AttemptTimeout` à **5 minutes**, calibrés pour les appels d'IA, plus le
   réessai du gestionnaire standard **au-dessus** des deux boucles de réessai
   applicatives. Sur le chemin d'attente d'une poignée de main TLS.

2. **La clé du réessai espacé est l'URL, jamais l'hôte.** Le certificat d'AC
   embarqué le montre : `igc-sante.esante.gouv.fr` sert `/AC/*.cer` (bloqué) et
   `/CRL/*.crl` (qui répondait encore, d'où le repli qui tenait). Un backoff par
   hôte aurait désactivé le dernier rempart. Verrouillé par
   `DownloadAsync_BacksOffPerEndpoint_NotGlobally`.

3. **La graine était déjà dans le dépôt.** `src/Api/Certs/` portait les quatre
   certificats IGC-Santé depuis le 2026-05-17, **référencés par zéro ligne de
   code** (`grep` sur `Certs`, `ACI-EL-ORG`, `ACR-EL` : aucun résultat). Ils
   sont déplacés dans `src/Application/Resources/IssuerCertificates/` et mis en
   service. Provenance, empreintes et procédure de rotation : le README du
   répertoire.

Le blocage a par ailleurs été **reproduit à la main** pendant l'instruction :
première requête `200 / 1856 octets`, deuxième `878 octets` de page de challenge
Incapsula. C'est le même phénomène que celui décrit dans l'énoncé, et il
confirme qu'un fichier de graine doit être vérifié comme DER avant d'être
committé (consigné dans la procédure de rotation).

### Effet de bord assumé — un message d'erreur corrigé

`ValidateCertificateOcspAsync` annonçait `Error processing the AIA extension`
quand le point d'accès répondait 403 : le message décrivait une analyse
d'extension alors que l'échec était un téléchargement. C'est cette formulation
que l'humain lisait dans Seq, et elle a coûté du temps d'instruction. Elle
devient `Failed to download issuer certificate. {cause}`. Un test existant a été
mis à jour en conséquence — c'est la seule attente de test modifiée.

### ⚠️ Réserve sur le Manual Test Plan, étape 1

L'attendu écrit est « **aucune** requête vers `igc-sante.esante.gouv.fr` ». La
graine supprime les requêtes vers `/AC/…` — c'est vérifiable et c'est l'objet de
la US. Mais **la requête OCSP elle-même reste un appel réseau par construction**
(c'est ce qu'est OCSP), et rien ne garantit que le répondeur nommé par le
certificat serveur MSSanté ne soit pas hébergé sur ce même domaine. Lire donc
l'attendu comme : **aucune requête vers `/AC/…`**, et au plus un aller-retour
vers le répondeur par fenêtre de fraîcheur (1 h par défaut, cache indexé par
numéro de série, partagé IMAP/SMTP).

### Validation

- Build : **0 erreur, 0 avertissement**
- Suite complète : **3 987 réussis, 0 échec**, 16 ignorés (5 projets)
- Tests de révocation ciblés : **76 réussis** (`~Services.Security`)
- Passe qualité `/simplify` : 3 nettoyages appliqués (constructeur primaire,
  surcharge de constructeur morte, niveau de journal de la suppression passé en
  Debug pour ne pas inonder le journal au moment où le service doit se taire),
  re-validation build + suite complète au vert.
- Les 3 rouges pré-existants attendus en suite complète (middleware DB-name,
  IMAP cancel, MailExport PDF) **ne se sont pas manifestés** sur ce run.

## Sonar log

**Mode A** (chaîné), `api-mail`, projet `healthplatform`, 2 analyses complètes.

### Findings sur le new code de task-288 : **zéro**

| Portée | Issues new-code | Hotspots à revoir |
|---|---|---|
| **Fichiers de task-288** | **0** | **0** |
| Projet entier (new-code period) | 66 | 2 |

Les 66 violations et les 2 hotspots viennent **intégralement de tasks déjà
mergées** que la période de new code du projet englobe encore — harnais k6
(`tests/loadtest-k6/report.py`, `journey.js` : 44 issues Python/JS, task-174),
tests d'embedding, `FlagsmithFeatureFlagService`, `MailRepository`,
`IheXdmProcessingService`. Vérifié fichier par fichier contre
`git diff --name-only origin/develop...HEAD` : **aucun recoupement**.

Les corriger ici reviendrait à greffer un diff Python/JS de 44 findings sur une
PR de sécurité C# — contraire aux règles 5 (1 US = 1 PR, ~30 fichiers) et 6
(scopes isolés). C'est le piège documenté par la mémoire
`project_sonar_new_code_baseline_includes_prior_tasks` : **un Quality Gate ERROR
sans dette introduite**.

### Quality Gate

| Condition | Valeur | Verdict | Imputable à task-288 ? |
|---|---|---|---|
| `new_coverage` | 88,5 % (seuil ≥ 80) | ✅ OK | — |
| `new_duplicated_lines_density` | 0,05 % (seuil ≤ 3) | ✅ OK | — |
| `new_security_hotspots_reviewed` | 83,3 % (seuil 100) | ❌ ERROR | **non** — 2 hotspots `python:S5332` dans `tests/loadtest-k6/` |
| `new_violations` | 66 (seuil 0) | ❌ ERROR | **non** — 0 dans les fichiers de la task |

**Quality Gate global : ERROR — inchangé par task-288, et non régressé par elle.**

### KPIs projet (baseline = final : aucune dette introduite)

| Métrique | Baseline | Final |
|---|---|---|
| Bugs | 2 | 2 |
| Vulnerabilities | 0 | 0 |
| Code smells | 64 | 64 |
| Security hotspots | 2 | 2 |
| Coverage | 88,2 % | 88,2 % |
| Duplication | 0,3 % | 0,3 % |
| Reliability rating | C | C |
| Security rating | A | A |
| Maintainability rating | A | A |

### Couverture des fichiers de la task

| Fichier | Couverture |
|---|---|
| `RevocationDownloadOutcome.cs` | 100 % |
| `SslTlsOptions.cs` | 100 % |
| `RevocationDownloadCoordinator.cs` | 96,2 % (0 ligne non couverte) |
| `OcspValidationService.cs` | 93,3 % |
| `EmbeddedIssuerCertificateSeed.cs` | **86,4 % → 93,2 %** |
| `CrlValidationService.cs` | 86,5 % |

Un seul correctif Sonar a été appliqué, et il porte sur la couverture : les
branches défensives de la graine (ressource embarquée illisible) n'étaient pas
exercées. Le projet de test embarque désormais un `CORRUPT.cer` délibérément
invalide et `Load` passe en `internal`. Ce n'est pas de la couverture pour la
couverture — c'est **la promesse du README qui devient vérifiable** : une graine
corrompue est ignorée, l'autorité repart en résolution AIA, le démarrage tient.
Restent 2 lignes non couvertes, la branche `stream == null` : `GetManifestResourceNames`
ne rend que des ressources existantes, elle est structurellement inatteignable.

### Correction apportée à `agents/sonar.md`

Le serveur est en **25.6.0.109173** → propriété `sonar.token`. Le tableau du
playbook affirmait « 9.9.8 vérifié le 2026-08-30 → `sonar.login` ». C'est la
**quatrième** bascule de version de ce conteneur ; le tableau est complété et
la consigne renforcée : exécuter le `curl /api/server/version`, ne jamais se
fier à la dernière ligne.

### `conventions/csharp.md`

**Aucune entrée à ajouter** : zéro règle Sonar corrigée manuellement sur le new
code. Les contrôles `awk` (S103) et `grep` (S125) passés avant le commit ont
tenu leur promesse — c'est précisément ce que le fichier de conventions vise.

## Lint / visuel

| Étape | Statut | Raison |
|---|---|---|
| `/lint-angular` | skip propre | `client-angular` non touché (`**Repos**: api-mail`) |
| `/lint-mobile` | skip propre | `client-mobile` non touché |
| `/verify-visual` | skip propre | aucun écran mobile touché — la US est entièrement backend |

## PRs

- `api-mail` : **[PR #216](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/216)** — label `awaiting-human-merge`
  - branche `fix/task-288-ocsp-crl-hardening`, 4 commits
- `dtos-mss` : branche créée par `/start` (auto-inclusion), **aucun commit** — la US ne
  change aucun contrat. Pas de PR, pas de publication NuGet.

## Code Review Summary

**Verdict : APPROVED** — 16 fichiers revus, **1 défaut bloquant trouvé et corrigé**,
2 suggestions non bloquantes, 1 dette de test pré-existante documentée.

### Le défaut trouvé par la revue (commit `83f4c0b`)

`RevocationDownloadCoordinator` comptait **un échec par appelant au lieu d'un par
téléchargement**. Avec la mutualisation, une rafale de 8 poignées de main sur un
téléchargement en échec portait le compteur à 8 — soit une fenêtre de **30 min
(le plafond) au lieu de 30 s**. Le sens est sûr, mais il contredit la règle 2, qui
demande une durée « courte devant le cache de succès, pour qu'un rétablissement soit
repris rapidement ». Corrigé test-first : l'initiateur est identifié par identité de
référence sur le `Lazy`, et lui seul compte l'échec.

> **Écart de procédure assumé.** `/review` ne corrige pas de code : il écrit
> `questions/` et arrête la chaîne. Ici, le défaut a été trouvé par la revue,
> il est cerné, sa correction fait 5 lignes et se prouve par un test RED→GREEN.
> Arrêter le cycle pour cela n'aurait servi personne. La correction est isolée
> dans son propre commit, et cette note existe pour que l'écart soit visible et
> non subi.

### Défaut d'isolation des tests — pré-existant, hors périmètre

| Base | Runs | Échecs |
|---|---|---|
| `origin/develop` (aucun code de task-288) | 12 | **4** (famille PdfPig `/F5`) |
| `fix/task-288-…` | 7 | 3 (PdfPig + `Assert.Single` sur `Meter` statique) |
| `fix/task-288-…`, collections xUnit sérialisées | 3 | **0** |

**Aucun test de task-288 n'a échoué une seule fois** (78/78 sur ~25 exécutions), et
aucun test défaillant ne touche un fichier de cette task.

Mécanisme isolé : `EnrichmentOperationScopeTests` capture un `Meter` **statique** et
filtre par `.Single(...)` ; il se protège en rejoignant la collection sérialisée
`MailMetricsCaptureCollection`, mais **~18 classes `ImapService*Tests` exercent
`ImapService`, qui émet les mêmes instruments via `EnrichmentOperationScope`, sans
rejoindre cette collection**.

→ **Mérite sa propre task** : la corriger ici toucherait 18 fichiers du module IMAP
sur une PR de révocation de certificats (règles 5 et 6).
