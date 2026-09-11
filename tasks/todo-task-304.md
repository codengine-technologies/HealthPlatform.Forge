# todo-task-304.md — Un seul mode de panne du serveur de messagerie est éprouvé (le mauvais mot de passe) : injecter la panne avec Toxiproxy, dont le client est déjà écrit et n'est utilisé par aucun test

**Repos**: api-mail
**Dependencies**: done-task-301
**Epic**: E016
**Single frontend**: true
**Priorité**: **4** — parallélisable avec `todo-task-302` et `todo-task-303`
dès que le contrat de `MailServerFixture` est publié par `todo-task-301`.
C'est la US qui rapproche le plus la suite de tests des incidents réellement
observés en campagne.

> **Origine** : audit de l'exploitation des tests d'intégration api-mail du
> 2026-09-11.

## Objective

Éprouver, contre un vrai serveur, ce que fait api-mail **quand le serveur de
messagerie va mal** : session coupée en cours d'usage, latence au-delà du
délai d'attente, poignée de main TLS tronquée, connexion refusée. Ces chemins
sont le cœur de la robustesse du pool de sessions et ils sont aujourd'hui
couverts **uniquement par des mocks**.

### Ce qui a été constaté (2026-09-11)

| Grandeur | Valeur constatée |
|---|---|
| Modes de panne du serveur éprouvés contre un vrai serveur | **1** — mot de passe erroné (`DovecotBenchSmokeTests.WildcardAuth_AcceptsAnyUser_AndRejectsWrongPassword`) |
| `DeadSessionPolicy` | **1** fichier de test, entièrement à mocks |
| `MailClientSessionManager` | **15+** fichiers de test, tous à mocks (dont `ImapServiceDeadSessionRetryTests`) |
| `ToxiproxyClient.cs` | **écrit** (`tests/mss.mail.loadtest.seed/`), référencé par **0** test |
| Conteneur Toxiproxy | **présent** dans le profil de banc de l'AppHost |

**Ce que les campagnes ont déjà observé en production de banc**, et qu'aucun
test ne reproduit : `SslHandshakeException` avec `IOException: Received an
unexpected EOF` (1 651 occurrences le 2026-08-01), `SocketException 10061
ConnectionRefused` provoquant un mur uniforme de ~2 060 ms sur toutes les
étapes IMAP (tir du 2026-08-25), et des rejets de connexion que Dovecot ne
journalise **pas** par connexion. Ces signatures sont documentées, datées, et
ne sont le sujet d'aucun test automatisé : quand elles reviendront, on les
re-diagnostiquera de zéro.

**L'outil est déjà là.** Toxiproxy tourne dans le profil de banc, et son
client C# est écrit et utilisé par l'outil de seed. Le brancher devant Dovecot
dans le harnais de test ne demande aucune brique nouvelle — seulement de
partager du code qui existe.

### Contenu attendu

1. **Toxiproxy dans le harnais de test**, devant Dovecot (et GreenMail pour
   les chemins d'envoi). Les suites existantes continuent de viser le serveur
   **en direct** : l'interposition n'est activée que pour les suites de panne,
   afin de ne pas ajouter un saut réseau — donc une source de variance — aux
   97 tests déjà verts.
2. **`ToxiproxyClient` partagé.** Il vit aujourd'hui dans l'outil de seed.
   Le déplacer dans `mss.mail.testing.shared` (déjà référencé par les projets
   de test et par le seed) plutôt que le dupliquer.
3. **Cinq familles de panne, une suite chacune** :
   - **Session coupée en cours d'usage** (`reset_peer` déclenché entre deux
     gestes du même praticien) : le geste suivant **aboutit**, par
     reconnexion. C'est l'assertion la plus précieuse de la US — elle éprouve
     `DeadSessionPolicy` pour de vrai.
   - **Latence au-delà du délai d'attente** (`latency`) : annulation propre,
     `ProblemDetails` typé (règle 12), aucune session laissée dans un état
     inutilisable, et **`OperationCanceledException` → 499** traitée
     centralement et non ré-attrapée par action.
   - **Poignée de main TLS tronquée** (`limit_data` pendant le handshake) :
     l'exception est gérée et convertie en erreur typée, pas en 500 nu. C'est
     la reproduction de l'`unexpected EOF` observé en campagne.
   - **Connexion refusée** (`down`) : erreur d'indisponibilité typée, et le
     temps de réponse est **borné** — pas un mur de deux secondes par
     tentative multiplié par le nombre de gestes.
   - **Débit dégradé sur le corps du message** (`bandwidth`) : le fetch
     partiel de l'archive `IHE_XDM.ZIP` reste **exact** — l'archive extraite
     est identique à l'archive semée. Une lenteur ne doit pas produire une
     troncature silencieuse : le nom de fichier déclenche la pipeline CDA,
     donc une archive tronquée deviendrait une perte de contenu clinique.
4. **Non-amplification.** Un échec ne doit pas déclencher une tempête de
   reconnexions : après une coupure, le nombre de tentatives de connexion est
   **borné et asserté**. Le repo a déjà payé une fois le prix d'une
   déduplication cassée sur un chemin de rafraîchissement — le même risque
   existe ici, et seul un test à serveur réel peut le montrer.
5. **Chaque suite nomme la signature d'incident qu'elle couvre**, en
   commentaire, avec la date de la campagne où elle a été observée. C'est ce
   qui fera qu'un rouge futur sera lu comme « le défaut du 2026-08-01 est
   revenu » et non comme un test obscur.

### Hors périmètre (explicite)

- **Les plafonds de concurrence du serveur** (`process_limit`,
  `client_limit`, `mail_max_userip_connections`) : ils se mesurent au banc,
  sous charge réelle, et six d'entre eux y ont déjà été instruits. Un test
  unitaire de panne ne les remplace pas.
- **La charge** : aucune montée en charge ici. Les tests de panne sont
  déterministes et courts ; la charge reste l'objet d'E015.
- **Les pannes côté base ou pooler** (`08P01`, `query_wait_timeout`) : elles
  ont leur propre US : `task-294`, mergée sur `develop` le 2026-09-10 (`tasks/archived/`).

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures) hors quarantaine déclarée
- [ ] `ToxiproxyClient` vit dans `mss.mail.testing.shared`, consommé par le
      seed **et** par les tests — aucune duplication de code
- [ ] Toxiproxy n'est interposé que pour les suites de panne ; les 97 tests
      `Server=real` préexistants visent toujours le serveur en direct et
      restent verts
- [ ] Test : session coupée en cours d'usage → le geste suivant du praticien
      **aboutit** (assertion sur le résultat métier, pas seulement sur
      l'absence d'exception)
- [ ] Test : latence > délai d'attente → annulation propre, `ProblemDetails`
      typé, `detail` sans trace ni donnée de santé ; aucune session inutilisable
      laissée derrière (vérifié par un geste suivant qui réussit)
- [ ] Test : handshake TLS tronqué → erreur typée, pas de 500 nu ; le
      commentaire de la suite cite la signature `unexpected EOF` du 2026-08-01
- [ ] Test : connexion refusée → erreur d'indisponibilité typée et **temps de
      réponse borné** (assertion sur la durée, pas seulement sur le statut)
- [ ] Test : débit dégradé → l'archive `IHE_XDM.ZIP` extraite est **strictement
      égale** à l'archive semée (comparaison d'octets)
- [ ] Test : nombre de tentatives de reconnexion après coupure **borné et
      asserté**
- [ ] **3 exécutions consécutives vertes** des suites de panne, consignées dans
      ce task file — l'injection de panne est la première source possible de
      flaky, et une suite de panne instable serait pire que pas de suite
- [ ] Chaque suite de panne porte en commentaire la signature d'incident
      couverte et la date de la campagne d'origine
- [ ] Aucune donnée de santé dans les journaux, les messages d'erreur ou les
      noms de toxics

## Manual Test Plan

- **Lancer les suites de panne** :
  `cd Api/Mail && dotnet test tests/mss.mail.integration.tests --no-build --filter "Server=real"`.
- **Ce que l'humain doit voir** : suite verte, nombre de tests `Server=real`
  en hausse d'au moins 6 par rapport à la référence de 97, et un conteneur
  `toxiproxy` vivant pendant l'exécution des seules suites de panne.
- **Contre-épreuve « la panne est vraiment injectée »** : pendant l'exécution,
  `docker exec <conteneur toxiproxy> /toxiproxy-cli list` doit montrer le proxy
  devant Dovecot et, à l'instant du test, le toxic actif. Un test de panne qui
  passe sans toxic actif ne prouve rien.
- **Contre-épreuve de reconnexion, à la main** : lancer l'application
  (`aspire run --project src/AppHost`), ouvrir la messagerie, puis
  `docker restart <conteneur dovecot>` et refaire un geste de lecture.
  **Ce que l'humain doit voir** : le geste aboutit après un court délai, sans
  message d'erreur technique et sans avoir à se reconnecter. C'est le
  comportement que la suite automatise.
- **Contre-épreuve de non-fuite** : lire les corps d'erreur produits par
  chacune des cinq familles. Aucun ne doit contenir de nom de serveur,
  d'identifiant de praticien, de sujet de message ni de nom de pièce jointe
  (un nom de pièce jointe désigne couramment le patient et l'examen).
- **Données de test** : 100 % synthétiques.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — robustesse du service MSSanté rendu au PS
- **Exigences DSR honorées** : non applicable directement ; la US sert la
  disponibilité et l'intégrité des échanges MSSanté
- **INS** : non applicable — corpus synthétique, aucun INS/NIR/NIA
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : la famille « débit dégradé » éprouve l'**intégrité** de
  l'archive IHE-XDM transportée, donc la non-corruption du document CDA avant
  validation Schematron par `interop-cda`. Une troncature silencieuse serait
  une perte de contenu clinique
- **Tracé PGSSI-S** : aucun évènement métier nouveau. La US vérifie que les
  erreurs d'indisponibilité sont journalisées côté serveur avec `traceId`
  (règle 12) et **sans** donnée de santé — y compris les noms de pièces
  jointes, exclus des étiquettes de télémétrie pour cette raison
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — conteneurs locaux, données synthétiques
- **AIPD / impact RGPD** : inchangée
