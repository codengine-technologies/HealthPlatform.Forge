# todo-task-302.md — Le serveur de test n'expose pas la capacité QUOTA : le chemin nominal de `MailboxQuotaService` est inatteignable, et le cloisonnement des boîtes entre praticiens n'est jamais éprouvé

**Repos**: api-mail
**Dependencies**: done-task-301
**Epic**: E016
**Single frontend**: true
**Priorité**: **4** — parallélisable avec `todo-task-303` et `todo-task-304`
dès que le contrat de `MailServerFixture` est publié par `todo-task-301` (pas
besoin d'attendre son merge : le contrat suffit).

> **Origine** : audit de l'exploitation des tests d'intégration api-mail du
> 2026-09-11.

## Objective

Doter le serveur IMAP **de test** des capacités que la production utilise et
que le serveur du banc n'expose pas — quota de boîte, dossiers spéciaux
complets, comptes distincts par praticien — afin que trois comportements
aujourd'hui invérifiables le deviennent : la lecture du quota, le classement
dans les dossiers spéciaux résolus par attribut, et **le cloisonnement de la
boîte d'un praticien vis-à-vis d'un autre**.

### Ce qui a été constaté (2026-09-11)

| Capacité | État du serveur de test | Conséquence mesurée |
|---|---|---|
| Plugin `quota` | **absent** de `src/AppHost/dovecot/dovecot.conf` | `MailboxQuotaService` teste `client.Capabilities.HasFlag(ImapCapabilities.Quota)` (`MailboxQuotaService.cs:103`) et retournerait **toujours** `Available = false`. Son chemin nominal est **inatteignable** contre un vrai serveur — il n'est couvert que par des mocks |
| `special_use` | `Sent`, `Drafts`, `Trash` seulement | `Junk` et `Archive` jamais résolus. L'absence est un **choix documenté du banc** (coût de `LIST` dans le scénario `folders`, comparabilité des campagnes) — pas un oubli |
| `passdb` | `static`, **un mot de passe pour tous** | Tout couple (utilisateur, `loadtest`) authentifie. Aucun test ne peut affirmer qu'un praticien ne lit pas la boîte d'un autre : l'assertion n'aurait aucun sens sur ce serveur |
| `protocols` | `imap` seul | L'envoi passe par GreenMail, dont `auth.disabled` accepte tout couple. Aucun échec SMTP AUTH éprouvable |

**La bonne réponse n'est pas de modifier la conf du banc.** Ses réglages sont
justifiés par la mesure, commentés ligne à ligne, et six plafonds de
concurrence y ont été instruits par des campagnes successives. Y ajouter des
dossiers et un plugin changerait le coût de `LIST` et romprait la
comparabilité des campagnes E015. La US crée donc une **conf de test dédiée**,
montée par le harnais de `todo-task-301`, et laisse `src/AppHost/dovecot/`
intact.

### Contenu attendu

1. **Conf Dovecot de test, distincte de celle du banc.** Dérivée de la conf de
   banc pour ce qui est du stockage et du TLS, elle porte en plus les
   capacités ci-dessous. Elle est montée par `MailServerFixture` ; la conf du
   banc reste **inchangée** (les `*BenchSmokeTests` continuent de monter la
   vraie, c'est leur objet).
2. **Capacité QUOTA activée** (plugin `quota` + `imap_quota` côté protocole +
   une `quota_rule` de stockage volontairement basse). Nouvelle suite à
   serveur réel :
   - la capacité est annoncée par le serveur et `GetQuotaAsync` renvoie
     `Available = true` ;
   - les valeurs lues (occupation, total, pourcentage) correspondent au corpus
     **réellement** semé, pas à une valeur arbitraire ;
   - le **dépassement** est exercé en remplissant la boîte au-delà de la règle,
     et ce que le service en fait est asserté.
   C'est la première fois que `GETQUOTAROOT` sera émis par la suite de tests.
3. **Dossiers spéciaux complets** : `Junk` et `Archive` déclarés en
   `special_use`, comme `Sent`/`Drafts`/`Trash`. Test : la résolution passe par
   **l'attribut** `special_use` et non par le repli sur le nom — c'est la voie
   réellement déployée depuis le correctif de résolution des dossiers
   spéciaux, et un test qui n'éprouverait que le repli laisserait passer une
   régression sur la voie principale.
4. **Comptes distincts par praticien** (`passdb` par fichier au lieu de
   `static`), et la suite qui en découle — **la plus importante de cette US** :
   un praticien authentifié avec ses propres identifiants **ne peut pas** lire,
   marquer ni déplacer un message de la boîte d'un autre praticien. Le
   cloisonnement des boîtes est aujourd'hui affirmé par l'architecture (une
   session IMAP par praticien, une base par praticien) et éprouvé **par aucun
   test à serveur réel**.
5. **Échec d'authentification différencié** : mot de passe invalide pour un
   utilisateur qui existe, utilisateur inexistant, et ce que le service
   remonte dans chaque cas — en `ProblemDetails` typé (règle 12), sans fuite du
   message brut du serveur.

### Hors périmètre (explicite)

- **La conf du banc de charge** (`src/AppHost/dovecot/dovecot.conf`) : non
  touchée. Toute évolution de ses capacités relève d'E015 et d'une campagne de
  mesure.
- **SMTP AUTH et les rejets d'envoi** (destinataire refusé, `SIZE`, bounce) :
  ils exigent un serveur SMTP authentifiant, donc un autre conteneur que
  GreenMail `auth.disabled`. Ils feront leur task si `todo-task-303` montre
  que les chemins d'envoi en ont besoin.
- **IDLE / CONDSTORE / QRESYNC** : ils n'ont d'intérêt qu'avec la sync
  incrémentale, qui n'est pas couverte par cette US.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures) hors quarantaine déclarée
- [ ] `git diff` sur `src/AppHost/dovecot/dovecot.conf` est **vide** ; la conf
      de test vit dans un fichier distinct, versionné, commenté sur ce qui la
      distingue de celle du banc et pourquoi
- [ ] Test : le serveur de test annonce `ImapCapabilities.Quota` (assertion sur
      la capacité elle-même, pas seulement sur le résultat du service)
- [ ] Test : `GetQuotaAsync` renvoie `Available = true` et des valeurs
      cohérentes avec le corpus semé (occupation non nulle, total égal à la
      règle configurée)
- [ ] Test : dépassement de quota exercé pour de vrai (boîte remplie au-delà de
      la règle) et comportement asserté
- [ ] Test : `Junk` et `Archive` résolus **par `special_use`** ; un test
      démontre que le repli par nom n'est pas la voie empruntée
- [ ] Test : un praticien authentifié n'accède pas à la boîte d'un autre —
      en lecture, en marquage **et** en déplacement (3 assertions distinctes)
- [ ] Test : mot de passe invalide et utilisateur inexistant produisent chacun
      un `ProblemDetails` typé, sans message brut du serveur dans le `detail`
- [ ] Les `*BenchSmokeTests` restent verts (ils montent toujours la conf du
      banc) ; les 97 tests `Server=real` préexistants restent verts
- [ ] Aucun mot de passe, INS ou identifiant réel dans la conf de test ni dans
      les journaux

## Manual Test Plan

- **Lancer la suite** : `cd Api/Mail && dotnet test tests/mss.mail.integration.tests --no-build --filter "Server=real"`.
- **Vérifier la capacité côté serveur, à la main** : pendant l'exécution,
  `docker exec <conteneur dovecot> doveadm quota get -u <utilisateur virtuel>`
  doit afficher une limite de stockage et une occupation non nulle. C'est la
  contre-épreuve indépendante du test.
- **Vérifier les dossiers** : `docker exec <conteneur dovecot> doveadm mailbox list -u <utilisateur virtuel>`
  doit lister `INBOX`, `Sent`, `Drafts`, `Trash`, `Junk`, `Archive`.
- **Ce que l'humain doit voir** : la suite verte, et le nombre de tests
  `Server=real` en hausse d'au moins 8 par rapport à la référence de 97.
- **Contre-épreuve du cloisonnement** : c'est l'assertion qui compte le plus
  dans un contexte de messagerie de santé. La vérifier à la main :
  `docker exec` puis une session IMAP avec les identifiants du praticien A
  demandant explicitement la boîte du praticien B → refus du serveur.
- **Contre-épreuve de non-régression du banc** : `dotnet test --filter "BenchSmokeTests"`
  reste vert, preuve que la conf du banc n'a pas bougé.
- **Données de test** : 100 % synthétiques, mots de passe factices versionnés
  dans la conf de test (jamais un secret réel, jamais une valeur issue de
  `.env`).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage de vérification interne. La US
  éprouve néanmoins une propriété de sécurité exigée par la PGSSI-S (voir
  ci-dessous)
- **Exigences DSR honorées** : non applicable directement ; le test de
  cloisonnement des boîtes documente une exigence de confidentialité MSSanté
- **INS** : non applicable — corpus synthétique, aucun INS/NIR/NIA
- **Authentification PS** : inchangée en production. Côté test, le serveur
  passe d'un mot de passe unique à des comptes distincts, **ce qui rapproche
  le harnais du comportement réel** d'un serveur MSSanté
- **Habilitations** : le test de cloisonnement éprouve qu'un PS n'accède qu'à
  sa propre boîte — propriété d'habilitation, jusqu'ici affirmée sans preuve
  exécutable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : aucun évènement métier nouveau. La US sert le
  référentiel **confidentialité / cloisonnement** : un accès croisé entre
  boîtes de PS deviendrait un test rouge au lieu d'un incident
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — conteneurs locaux, données synthétiques
- **AIPD / impact RGPD** : inchangée
