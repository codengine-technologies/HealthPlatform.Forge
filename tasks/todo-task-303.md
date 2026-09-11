# todo-task-303.md — Aucune requête HTTP ne traverse un vrai serveur IMAP : 55 endpoints dépendants de la messagerie sont validés contre des mocks, jamais contre la chaîne réelle

**Repos**: api-mail
**Dependencies**: done-task-301
**Epic**: E016
**Single frontend**: true
**Priorité**: **3** — plus fort rendement de l'EPIC. Parallélisable avec
`todo-task-302` et `todo-task-304` dès que le contrat de `MailServerFixture`
est publié par `todo-task-301`.

> **Origine** : audit de l'exploitation des tests d'intégration api-mail du
> 2026-09-11.

## Objective

Faire exister le montage qui manque : une requête HTTP réelle, entrant par le
pipeline `Program` complet, servie par api-mail, jusqu'à un **vrai** serveur
IMAP/SMTP — et l'utiliser pour couvrir les endpoints de messagerie, en
commençant par ceux dont le banc de charge prouve déjà l'atteignabilité.

### Ce qui a été constaté (2026-09-11)

| Grandeur | Valeur constatée |
|---|---|
| Actions HTTP dans `src/Api` | **146** |
| dont structurellement dépendantes d'IMAP/SMTP | **55** (`MailController` 38, `DraftController` 6, `SyncController` 6, `MailExportController` 3, `AccountController` 2) |
| Actions couvertes par un test HTTP à serveur réel | **0** |
| Usages de `WebApplicationFactory` dans les tests api-mail | **0** — les deux seules occurrences du nom sont des **commentaires** disant qu'il en faudrait un (`AiDiagnosticsControllerTests.cs:24`) ou qu'il n'est pas utilisé (`SearchScenarioTests.cs:35`) |
| Montage des tests HTTP existants | `WebApplication.CreateBuilder()` + `UseTestServer()` **ad hoc**, contrôleurs enregistrés à la main, `IImapService` substitué (`MailExportControllerIntegrationTests.cs:98` et `:123`) |
| Routes HTTP que le banc k6 conduit déjà sur la chaîne réelle | **13** (`lib/routes.js`) — avec des contrôles de vivacité, **aucune assertion fonctionnelle** |

**Le défaut de fond : deux populations qui ne se rencontrent jamais.** Les
suites à serveur réel appellent les services **directement depuis un scope
DI** ; les suites HTTP montent un `TestServer` ad hoc et **substituent** IMAP.
Rien ne valide donc, contre un serveur réel : le binding de modèle, le header
`Client-Session-Id` qui pilote le pool de sessions, le mapping `ProblemDetails`
d'une panne IMAP (règle 12), le limiteur de débit, l'authentification, la
sérialisation des DTO, le SSE. La règle 1b de `CLAUDE.md` — « chaque endpoint
a au moins un test d'intégration » — est honorée sur la lettre et pas sur
l'intention.

**Et l'infrastructure existe déjà.** Le banc de charge conduit cette chaîne
complète en s'authentifiant par `TestBypassAuthenticationHandler`, qui est
**du code de production** (`src/Api/Authentication/`, clé `TestMode:BypassKey`,
mot de passe `TestMode:Password`). Ce qui manque n'est pas un mécanisme, c'est
un `HttpClient` xUnit et des assertions.

### Deux contraintes techniques connues d'avance

1. **`Program` est un `public static class`** (`src/Api/Program.cs:33`), donc
   il **ne peut pas** servir de paramètre de type à
   `WebApplicationFactory<TEntryPoint>` (un type statique n'est pas un
   argument générique valide). Il faut soit un type marqueur non statique dans
   l'assembly d'API, soit un `partial class Program` — décision de
   `/develop`, mais elle doit être **explicite et commentée**, pas découverte
   en cours de route.
2. **`Program` appelle `builder.AddServiceDefaults()` et
   `app.MapDefaultEndpoints()`** (lignes 42 et 220), donc le pipeline embarque
   les défauts Aspire (télémétrie, sondes). Le harnais doit neutraliser ce qui
   sort du processus (exporteurs OTLP) sans court-circuiter le pipeline
   testé — sinon on ne teste plus `Program` mais une copie.

### Contenu attendu

1. **`MailApiFactory`** : un `WebApplicationFactory` qui démarre le pipeline
   `Program` réel, surcharge la configuration `MailServers:Domains:*` avec les
   ports du harnais de `todo-task-301` (ce que `MailServerTestHarness`
   produit déjà), pose `TestMode:BypassKey` / `TestMode:Password`, et branche
   le Postgres/Redis conteneurisés. Un `HttpClient` authentifié par le header
   de bypass, comme le fait le banc.
2. **Première vague de couverture : les 13 routes du banc**, parce que leur
   atteignabilité est déjà prouvée par des campagnes — liste des mails d'un
   dossier, contenu d'un message, dossiers, dossier du jour, enrichissement
   synchrone, téléchargement de pièce jointe, marquage lu, couverture de
   sync, envoi, recherche. Chaque test asserte la **charge utile** (contenu,
   UID, nombres), pas seulement le code HTTP : le corpus semé est déterministe,
   donc les valeurs attendues sont exactes.
3. **Kestrel réel pour les endpoints qui streament.** `MailExportController`
   est testé aujourd'hui sur `TestServer`, or il est **vérifié (2026-09-08)**
   que `TestServer.AllowSynchronousIO = false` ne refuse **pas** une écriture
   synchrone dans `Response.Body` : la sonde répond 200 sans lever. Un export
   réel, d'un mail réel, à travers Kestrel réel est le seul montage où une
   écriture synchrone se manifeste — c'est exactement la classe de défaut
   qu'un test sur `MemoryStream` laisse passer.
4. **Le header `Client-Session-Id` devient observable.** Deux requêtes du même
   praticien avec le même identifiant de session réutilisent la session IMAP ;
   avec deux identifiants différents, elles n'en partagent aucune. C'est le
   cœur du pool, aujourd'hui éprouvé uniquement par des tests à mocks.
5. **Panne IMAP → `ProblemDetails` typé.** Une instance pointée sur un port
   fermé doit rendre un `application/problem+json` de statut approprié, avec
   un `detail` **exempt** de message brut du serveur, de trace, et de toute
   donnée de santé (règle 12, garde-fou de non-fuite).
6. **Table de couverture des 55 actions** tenue dans le task file : couverte /
   non couverte / hors atteinte, avec le motif. C'est elle qui rendra la
   règle 1b mesurable au lieu de déclarative, et qui fixera le périmètre des
   vagues suivantes.

### Hors périmètre (explicite)

- **Les 91 actions non dépendantes d'IMAP/SMTP** (contacts, patients,
  signatures, IA, audit…) : elles ont leur propre couverture et n'ont rien à
  gagner à un serveur de messagerie.
- **Les modes de panne du serveur** (latence, coupure en cours de session,
  reset TLS) — objet de `todo-task-304`. Cette US n'éprouve que le cas
  « serveur injoignable », qui ne demande aucun outil.
- **La couverture exhaustive des 38 actions de `MailController`** : cette US
  livre le montage plus la première vague. Les vagues suivantes se priorisent
  sur la table de couverture qu'elle produit.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures) hors quarantaine déclarée
- [ ] `MailApiFactory` démarre le pipeline `Program` réel (pas un
      `WebApplication.CreateBuilder()` ad hoc) ; le choix de type d'entrée est
      commenté avec la raison (contrainte du `static class Program`)
- [ ] Au moins **13 endpoints** couverts par un test HTTP bout-en-bout contre
      Dovecot/GreenMail réels, chacun assertant la charge utile et non
      seulement le statut HTTP
- [ ] Au moins un endpoint de streaming (`MailExportController`) testé à
      travers **Kestrel réel**, avec réinjection de la régression : un test
      démontre que le montage **détecte** une écriture synchrone dans
      `Response.Body` (sinon le montage ne prouve rien)
- [ ] Test : deux requêtes de même `Client-Session-Id` réutilisent la session
      IMAP ; deux identifiants distincts n'en partagent aucune — observé côté
      serveur (nombre de connexions), pas seulement par un compteur applicatif
- [ ] Test : serveur IMAP injoignable → `application/problem+json`, statut
      typé, et le `detail` ne contient ni trace, ni message brut du serveur,
      ni donnée de santé
- [ ] Table de couverture des 55 actions dépendantes d'IMAP/SMTP consignée
      dans ce task file
- [ ] Les 97 tests `Server=real` préexistants restent verts
- [ ] Durée de la population `Server=real` mesurée avant/après via
      `Tools/timing/measure.sh --kind test` et consignée
- [ ] Aucune donnée de santé dans les corps de réponse asserté, les journaux
      ni les messages d'erreur de test

## Manual Test Plan

- **Lancer l'application** pour comparer à la main :
  `cd Api/Mail && aspire run --project src/AppHost` (profil de développement).
- **Lancer la nouvelle suite** :
  `dotnet test tests/mss.mail.integration.tests --no-build --filter "Server=real"`.
- **Ce que l'humain doit voir** : la suite verte, et le nombre de tests
  `Server=real` en hausse d'au moins 13 par rapport à la référence de 97.
- **Contre-épreuve « le montage traverse bien la chaîne »** : arrêter le
  conteneur Dovecot **pendant** l'exécution d'un test de lecture
  (`docker stop`), et constater que le test échoue avec une erreur de
  connexion — s'il reste vert, un mock s'est glissé dans le montage.
- **Contre-épreuve du streaming** : appeler l'export depuis le navigateur sur
  l'application lancée, sur un mail réel du corpus, et vérifier que le
  fichier téléchargé s'ouvre. Puis vérifier que le test automatisé couvre le
  même chemin (même endpoint, même mail).
- **Contre-épreuve de non-fuite** : lire le corps de la réponse d'erreur quand
  le serveur est injoignable. **Ce que l'humain doit voir** : `title` et
  `detail` génériques, un `traceId`, et rien qui ressemble à un nom de serveur,
  un identifiant de praticien ou un sujet de message.
- **Données de test** : 100 % synthétiques (corpus `MailboxCorpus`,
  utilisateurs virtuels, RPPS fictifs).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage de vérification interne. La US
  éprouve toutefois deux exigences transverses : non-fuite de données de santé
  dans les erreurs, et cloisonnement par session
- **Exigences DSR honorées** : non applicable directement ; la US rend
  vérifiable le comportement des endpoints MSSanté déjà référencés
- **INS** : non applicable — corpus synthétique. **Garde-fou** : aucun test ne
  doit introduire d'INS, de NIR ou de NIA, même factice au format réel
- **Authentification PS** : le harnais utilise le bypass de test
  (`TestMode:BypassKey`), mécanisme **déjà présent en production** et déjà
  utilisé par le banc. Aucun assouplissement nouveau de l'authentification
  n'est introduit, et le bypass reste inopérant sans la clé configurée
- **Habilitations** : le test de session éprouve qu'un praticien n'emprunte pas
  la session d'un autre
- **Interop CI-SIS** : les tests d'enrichissement traversent la pipeline
  CDA/IHE-XDM sur les archives synthétiques déjà versionnées ; aucun nouveau
  volet, aucun nouveau format
- **Tracé PGSSI-S** : aucun évènement métier nouveau. La US ajoute une
  assertion de **non-fuite** sur le contenu des `ProblemDetails` (règle 12)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — conteneurs locaux, données synthétiques
- **AIPD / impact RGPD** : inchangée
