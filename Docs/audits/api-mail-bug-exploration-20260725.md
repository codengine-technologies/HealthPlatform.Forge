# Exploration de bugs `api-mail` — 2026-07-25

> **Nature** : audit de code exploratoire, **lecture seule**. Aucun code modifié,
> aucune opération git.
> **Méthode** : six explorations parallèles indépendantes sur six axes distincts,
> puis vérification des findings les plus graves directement dans le code par le PO.
> **Périmètre** : `Api/Mail` (branche `feat/task-173-loadtest-bench-greenmail` au
> moment de l'audit).
> **Sortie** : 20 US rédigées (`tasks/todo-task-175.md` → `todo-task-194.md`) +
> le présent inventaire, qui conserve la trace des findings **non** convertis.

---

## 1. Ce qu'il faut retenir

**Trois axes indépendants ont trouvé le même défaut critique** — le flux SSE
d'évènements mail est indexé sur le nom de dossier et non sur la boîte du
praticien, si bien qu'un praticien reçoit les messages d'un autre, contenu
clinique compris. Cette convergence, obtenue sans concertation entre les agents,
est le signal le plus fort de l'audit (task-175).

**Deux incidents relèvent d'un traitement humain immédiat**, hors cycle forge :
un secret vivant committé (task-177) et l'envoi de contenu clinique à un
fournisseur d'IA hors périmètre HDS (task-178).

**Un motif se répète** dans plusieurs findings : le repo **connaît** la bonne
pratique, l'applique à un endroit, et l'oublie à côté. Le broker de notifications
est correctement cloisonné par praticien, celui des évènements mail non ; le ZIP
bufferise ses écritures, le PDF non ; l'export PDF est journalisé, le
téléchargement de pièce jointe non ; `SetId` refuse une valeur dégénérée,
`DocumentId` en fabrique une ; le chemin sortant nettoie son fichier temporaire,
les deux chemins entrants non ; `task-071` a assaini le log nominal de recherche,
le log d'erreur juste à côté est passé au travers. Ce ne sont pas des arbitrages,
ce sont des asymétries — et c'est ce qui les rend corrigeables sans débat de fond.

---

## 2. Findings convertis en US

| US | Titre | Gravité | Axe | Vérifié par le PO |
|---|---|---|---|---|
| [task-175](../../tasks/todo-task-175.md) | Fuite inter-praticiens sur le flux SSE (clé = dossier) | critique | HTTP + async + IMAP | oui |
| [task-176](../../tasks/todo-task-176.md) | Documents sans INS agrégés sur un patient arbitraire | critique | données + métier | oui |
| [task-177](../../tasks/todo-task-177.md) | Secrets vivants committés (OpenAI, FHIR ANS, mots de passe) | critique | sécurité | oui |
| [task-178](../../tasks/todo-task-178.md) | Contenu clinique envoyé à OpenAI par défaut | critique | sécurité | oui |
| [task-179](../../tasks/todo-task-179.md) | Identité mail sans UIDVALIDITY : mauvais contenu servi | critique | IMAP | oui |
| [task-180](../../tasks/todo-task-180.md) | PJ identifiées par nom : mauvais fichier, perte silencieuse | critique | métier | oui |
| [task-181](../../tasks/todo-task-181.md) | PJ et IHE_XDM invisibles sans `Content-Disposition` | majeur | métier | non |
| [task-182](../../tasks/todo-task-182.md) | Dossiers exclus par sous-chaîne (« Consentements » ⊃ « sent ») | majeur | métier | oui |
| [task-183](../../tasks/todo-task-183.md) | `X-MSS-INS: O` pour une INS non qualifiée ; OID perdu | majeur | métier | non |
| [task-184](../../tasks/todo-task-184.md) | INS dans les URL, données patient dans les logs | majeur | sécurité | oui |
| [task-185](../../tasks/todo-task-185.md) | Archives IHE_XDM en temp jamais supprimées | majeur | sécurité + async | oui |
| [task-186](../../tasks/todo-task-186.md) | Audit PGSSI-S : PJ non tracées, traces perdues sous charge | majeur | sécurité + async | oui |
| [task-187](../../tasks/todo-task-187.md) | Sessions IMAP détruites en cours d'usage | majeur | IMAP + async | non |
| [task-188](../../tasks/todo-task-188.md) | Plan de contrôle sync : pause inopérante, état perdu | majeur | IMAP + async | non |
| [task-189](../../tasks/todo-task-189.md) | Purge non gardée, corps invalide en 500, GET qui écrit | majeur | HTTP | oui |
| [task-190](../../tasks/todo-task-190.md) | Impression/export PDF : 500 sous Kestrel ; tableaux collés | majeur | HTTP + métier | non |
| [task-191](../../tasks/todo-task-191.md) | Ingestion : FK, doublons de patients, horodatages mixtes | majeur | données | oui (FK) |
| [task-192](../../tasks/todo-task-192.md) | Recherche : déduplication sur l'UID, casse | majeur | métier | non |
| [task-193](../../tasks/todo-task-193.md) | CDA sans identifiant : doublon inter-patients, document masqué | majeur | métier | non |
| [task-194](../../tasks/todo-task-194.md) | Balayage complet par page ; historique patient non paginé | majeur (perf, **E011**) | données | non |

« Vérifié par le PO » = relecture directe du code cité, au-delà du rapport de
l'agent. Les findings non vérifiés reposent sur le rapport d'agent avec
`file:line` : à confirmer par `/develop` avant correctif.

---

## 3. Findings **non** convertis en US

Conservés ici pour ne rien perdre. À arbitrer : soit une US ultérieure, soit un
traitement opportuniste lors d'une intervention sur le fichier concerné.

### 3.1 Mineurs à traiter à l'occasion

| # | Finding | Emplacement | Pourquoi non converti |
|---|---|---|---|
| 1 | Clé de cache OCSP = numéro de série **seul** (unique par AC seulement) ; cache d'émetteurs statique non borné et non purgé ; `HttpResponseMessage` non libérée | `OcspValidationService.cs:55,283,357-365,406-411` | Impact réel conditionné à une chaîne multi-AC ; la posture OCSP/CRL arbitrée est par ailleurs **conforme** (voir § 4) |
| 2 | État de conversation IA = `List<>` mutable partagée dans un singleton, mutée par une tâche non attendue portant le jeton d'annulation de la requête | `AiConversationService.cs:243,464-499` | Peut produire un 500 sporadique et une perte de compaction ; pas d'impact clinique |
| 3 | `From:` et `Message-ID:` repris **verbatim** du client, jamais confrontés à la boîte authentifiée | `SmtpService.cs:150-163,228-237,267-307` | À requalifier : **majeur** si l'opérateur MSSanté relaie un `From` divergent. Recommandé pour la prochaine vague |
| 4 | Clé de contrôle INS : départements corses `2A`/`2B` rejetés ; pivot de siècle plaçant une naissance de 1925 en 2025 ; `IsQualified` confondu avec la validité du checksum | `InsValidationService.cs:20-30,62-73` | Bloque un patient corse légitime — **recommandé pour la prochaine vague** (identito-vigilance) |
| 5 | `MailSignatureRepository.UpdateAsync` sans prédicat de propriété (le contrôleur garde en amont) | `Repositories/MailSignatureRepository.cs:64-74` | **Non atteignable** aujourd'hui ; défaut de placement d'invariant |
| 6 | Accusé de lecture émis comme mail lisible avec en-tête maison, non conforme RFC 3798 (`multipart/report`) ; aucun analyseur DSN/MDN **entrant** | `MdnService.cs` | Écart de conformité fonctionnel, pas un bug — relève du backlog produit MSSanté |
| 7 | `TextChunkingService` est du **code mort** (aucun appelant en production) ; le chemin réel tronque à 4 000 / 20 000 caractères | `TextChunkingService.cs`, `AddNewMailConsumer.cs:186-189` | Rappel sémantique réduit sur les longs comptes-rendus — sujet de qualité IA, pas un défaut |
| 8 | `MdnService.BuildMdnMessage` mêle l'UTC stocké et `DateTime.Now` | `MdnService.cs:106-107` | Cosmétique |

### 3.2 Vérifié **sain** — ne pas re-auditer

Résultats négatifs utiles, obtenus en vérifiant :

- **Cloisonnement inter-praticiens hors SSE** : une base par praticien
  (`UserContextInfo.UserDatabaseName` → `BaseRepository`), dont aucun paramètre de
  requête ne peut changer le nom. Les requêtes non filtrées des contrôleurs de
  diagnostic ne sont donc **pas** une fuite inter-tenant. La fuite de task-175
  vient uniquement du fan-out **en mémoire**.
- **Posture OCSP/CRL conforme à l'arbitrage** (grâce de 4 h sur cache périmé puis
  fail-close ; révoqué = refus immédiat sans grâce). Les quatre rappels de
  validation de certificat délèguent correctement ; les seuls `return true`
  inconditionnels sont dans des fixtures de test.
- **`GlobalExceptionHandler`** : mapping par type d'exception, détail 5xx générique
  constant, aucune fuite de trace ni de message système (règle 12 respectée sur ce
  composant).
- **Appariement patient par traits** : `MatchByTraitsAsync` classe des candidats
  pour un choix **humain** ; aucun rattachement automatique par nom/date de
  naissance. `AttachDocumentToPatientAsync` exige un identifiant patient explicite.
- **Décodage MIME** (charset, RFC 2047, RFC 2231) entièrement délégué à MimeKit ;
  aucune hypothèse `Encoding.Default`/ASCII/latin-1 ; noms accentués préservés en
  réponse (RFC 5987).
- **Cascades de suppression** : les auto-références (`DuplicateOfId`,
  `SupersededByDocumentId`, `SuppressionRequestedByMailId`) sont en `SetNull` —
  mettre une ancienne version à la Corbeille ne peut pas emporter un document plus
  récent. Le modèle EF et le schéma FluentMigrator concordent.
- **Hygiène asynchrone générale** : aucun `async void`, aucun `.Result`/`.Wait()`
  hors des cas signalés, aucun `new HttpClient()` en production, aucune dépendance
  captive (les scopes sont validés en développement).
- **Règle 7c (migrations EF)** : **sans objet** ici — le schéma est géré par
  **FluentMigrator**, pas par EF Core. Il n'existe ni snapshot ni `.Designer.cs`
  susceptible de dériver. Contrepartie : rien ne garde mécaniquement la cohérence
  modèle/schéma — c'est ainsi que l'incohérence d'horodatage de task-191 a survécu.
- **Secret Gmail** connu du workspace : **absent** de `api-mail` (seuls des noms
  d'hôtes d'autodiscovery `imap.gmail.com` / `smtp.gmail.com` sont présents). Il est
  donc dans un autre repo.

---

## 4. Suites recommandées

1. **Hors forge, immédiat** : rotation des secrets et décision sur la réécriture
   d'historique (task-177) ; qualification DPO du routage IA (task-178).
2. **Puis** task-175 (fuite SSE) : correctif serré, testable, à fort impact.
3. **Prérequis technique** : `api-mail` est sur `feat/task-173-loadtest-bench-greenmail`
   au moment de l'audit — le pré-vol de `/start` exige `develop` sur tous les repos
   automatisés. Terminer ou ranger task-173 avant de lancer ce lot.
4. **Ordonnancement suggéré** : les tasks 176, 191 et 183 touchent toutes le
   rattachement patient ; les enchaîner dans cet ordre limite les conflits.
   Les tasks 179 et 192 partagent l'identité des mails : livrer 179 d'abord.
5. **Quatre tasks appellent un arbitrage humain** documenté dans leur corps :
   task-178 (fournisseur d'IA autorisé), task-183 (NIA, OID de test, fusion
   rétroactive), task-176 et task-191 et task-193 (remédiation des données déjà
   affectées, sur inventaire).
