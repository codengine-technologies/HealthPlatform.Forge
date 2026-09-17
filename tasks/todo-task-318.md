# todo-task-318.md — Le jeton PSC est vérifié, et il désigne le même professionnel que le compte connecté

**Repos**: api-mail
**Dependencies**: —
**Epic**: E016
**Single frontend**: true

> Remédiation n°1 de l'audit sécurité du registre du 2026-09-16 (écart critique).
> Les deux autres écarts majeurs sont task-319 (re-validation continue) et
> task-320 (hors ligne en lecture seule côté serveur).

## Objectif

Aujourd'hui, `api-mail` **croit sur parole** le jeton Pro Santé Connect que le client
lui présente dans l'en-tête `X-PSC-Token` : il le décode sans en vérifier la
signature, et rien ne relie l'identité PSC qu'il y lit au compte Keycloak qui fait
la requête. La seule autorité réelle est la sonde IMAP chez l'opérateur MSSanté, au
moment du rattachement.

Conséquence : **n'importe quel compte Keycloak muni d'un jeton PSC valide d'un
autre professionnel** peut rattacher la messagerie de ce professionnel sur son
propre compte, l'y ancrer, en lire tout le contenu synchronisé hors ligne pour une
durée indéfinie, et **verrouiller la victime** (« ce RPPS est déjà rattaché à un
autre compte ») sans qu'aucun chemin de correction n'existe (l'accès admin est
bloqué, cf. `questions/task-302.md`). Le vol de jeton n'est pas théorique : le
client mobile le conserve dans le stockage local du navigateur, et le proxy le
remet au client dans l'agrégat de connexion.

Après cette US, deux règles tiennent :

1. **Un jeton PSC n'est cru qu'une fois vérifié** — signature, émetteur, validité.
2. **Le professionnel du jeton PSC est le professionnel du compte Keycloak.** Le
   rattachement, l'ancrage et la compatibilité de session reposent sur cette
   égalité, pas sur la seule réussite d'une sonde.

**US backend uniquement (justification)** : aucune route nouvelle, aucun contrat
DTO modifié. Les refus sortent en `ProblemDetails` (règle 12) avec des codes que
les trois fronts savent déjà afficher (`PscIdentityConflict`, `PscMismatch`). Le
correctif structurel à plus long terme, qui retire le transit du jeton PSC par le
client, reste **task-171** (backend pull via proxy, en attente) : cette US n'en
dépend pas et ne le remplace pas.

## Constat établi par lecture du code (2026-09-16)

- `Api/Mail/src/Api/Middleware/UserContextEnricherMiddleware.cs` — `ResolvePscToken`
  lit l'en-tête tel quel ; `TryParsePscIdentity` décode le JWT **sans validation de
  signature** (documenté comme tel) et en tire `sub` + `SubjectNameID`.
- Même fichier, `ApplyAuthenticatedUserAsync` — le cross-check PSC/KC de task-048 a
  été **retiré** par task-308 parce que les claims `mssSub` / `mssRpps` ont disparu du
  realm. Depuis, **plus aucune ligne** ne rapproche l'identité Keycloak de l'identité
  PSC.
- `Api/Mail/src/Application/Services/Mailboxes/MailboxManagementService.cs` —
  `AttachAsync` sonde l'opérateur avec `(adresse, jeton)` puis enregistre
  `ValidatedByPscSubject` / `ValidatedByRpps` **lus du jeton non vérifié**. Le compte
  Keycloak appelant est ancré sur cette identité au premier rattachement.
- `Api/Mail/src/Infrastructure/Repositories/TenantDb/PostgresTenantRegistryClient.cs`
  — `AttachMailboxCoreAsync` refuse un RPPS déjà porté par un autre compte : c'est
  ce qui **verrouille la victime** une fois l'attaquant passé le premier.
- Côté proxy (`psc-auth-proxy`, hors automation) : le jeton Keycloak est obtenu par
  **JWT Authorization Grant (RFC 7523)** avec le jeton PSC en assertion — Keycloak
  connaît donc le lien entre l'utilisateur Keycloak et l'identité PSC (« identity
  not linked » est une erreur qu'il renvoie). Cette liaison existe ; elle n'est
  simplement **pas exposée** à `api-mail`.

## Règles métier

**RG-1 — Vérification cryptographique du jeton PSC.** Avant toute lecture de ses
claims, `api-mail` valide le jeton PSC : signature contre les clés publiées par
l'émetteur PSC configuré (JWKS), émetteur attendu, fenêtre de validité (`exp`,
`nbf`, tolérance d'horloge alignée sur celle du bearer Keycloak). Les émetteurs
acceptés sont **une liste de configuration** (production, bac à sable), jamais un
littéral.

**RG-2 — Un jeton PSC invalide est un refus, pas un mode hors ligne.** Signature
fausse, émetteur inconnu, jeton malformé : la requête est refusée en 401
`ProblemDetails` avec un code dédié, et l'évènement est journalisé (technique,
sans le jeton). Un jeton simplement **expiré** conserve le comportement actuel
de task-165 (401, refresh réactif des fronts). On ne dégrade **jamais**
silencieusement vers le hors ligne : cela masquerait une attaque derrière un
comportement normal.

**RG-3 — Liaison compte ↔ professionnel.** Le jeton Keycloak porte l'identifiant
PSC de l'utilisateur lié (claim émis par Keycloak depuis la liaison
d'identité fédérée — voir l'encadré d'arbitrage). Au **rattachement** et à
**l'évaluation de compatibilité**, `api-mail` exige l'égalité entre ce claim et le
`sub` du jeton PSC vérifié. Inégalité → 409 `PscIdentityConflict`, aucun ré-ancrage,
rien de persisté.

**RG-4 — Déploiement en deux temps, comme task-048.** Un réglage `Enforce`
gouverne RG-3 : en mode observation, l'inégalité est journalisée (identifiants
tronqués, jamais le jeton) et la requête passe ; en mode strict, elle est
refusée. RG-1 et RG-2, elles, sont **strictes dès la livraison** : un jeton non
signé n'a aucune raison légitime d'exister.

**RG-5 — Le banc de charge continue de tourner.** Le chemin de contournement de
test (`X-Test-Bypass`, hors Production) n'est pas concerné par RG-1 à RG-3 : le
banc forge ses jetons. Aucune régression sur task-311.

**RG-6 — Trace d'audit.** Un rattachement refusé pour conflit d'identité produit
une trace `MailboxAttached` avec `Success = false` et le code de refus en
`ErrorMessage`. **Aucun nouveau membre** n'est ajouté à `AuditActionType` : ce
type est miroité à la main côté Angular et Blazor, et l'US doit rester backend
(cf. mémoire `auditactiontype-ordinal-wire-mirrored-ts`).

> ⚠️ **Arbitrage humain requis — avant `/start`, pas pendant.**
>
> 1. **Le claim de liaison Keycloak.** RG-3 suppose un *protocol mapper* dans le
>    realm `weda-realm` qui expose l'identifiant PSC de l'identité fédérée liée à
>    l'utilisateur (par exemple `psc_sub`). Le realm est hors automation de la
>    forge : c'est vous qui le configurez. Confirmez le **nom du claim** et son
>    contenu exact (le `sub` PSC tel qu'il apparaît dans le jeton PSC, sans
>    transformation).
> 2. **Les émetteurs PSC autorisés** par environnement (URL d'émetteur et JWKS
>    de production et du bac à sable ANS), pour la configuration de RG-1.
> 3. **La durée du mode observation** de RG-4 avant passage en strict.
>
> Le développement peut commencer sur RG-1, RG-2, RG-5 et RG-6 sans ces réponses ;
> RG-3 et RG-4 se branchent sur le nom du claim dès qu'il est connu.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] Le jeton PSC est validé (signature JWKS, émetteur, validité) **avant** toute lecture de `sub` / `SubjectNameID` ; émetteurs et JWKS viennent de la configuration
- [ ] Un jeton PSC forgé (non signé ou signé par une clé inconnue) est refusé en 401 `application/problem+json` avec un code dédié, sur toute route qui le lirait
- [ ] Un jeton PSC expiré conserve le comportement task-165 (401, code existant)
- [ ] Le rattachement exige l'égalité entre le claim de liaison Keycloak et le `sub` PSC vérifié ; inégalité → 409 `PscIdentityConflict`, rien de persisté
- [ ] La compatibilité de session (`MailboxCompatibility`) refuse une identité PSC qui n'est pas celle liée au compte Keycloak
- [ ] Réglage `Enforce` : observation (journal seul) / strict (refus), avec valeur par défaut documentée dans `appsettings.json`
- [ ] Le chemin `X-Test-Bypass` (hors Production) n'est pas soumis à la validation PSC ; le banc de charge (`aspire run` profil loadtest) passe sans changement
- [ ] Trace `MailboxAttached` `Success = false` sur refus d'identité ; aucun nouveau membre `AuditActionType`
- [ ] Aucune trace du jeton PSC (même partiel) dans les logs ; identifiants tronqués comme dans task-048
- [ ] Tests unitaires : validation de jeton (signé valide / signature fausse / émetteur inconnu / expiré / malformé), liaison (égalité / inégalité / claim absent en observation / claim absent en strict)
- [ ] Tests d'intégration : `POST /api/v1/account/mailboxes` avec jeton PSC forgé → 401 ; avec jeton valide mais identité ≠ compte → 409 ; `GET /api/v1/account/mailboxes` avec jeton forgé → 401
- [ ] Le document d'EPIC E016 (`/tech-writer`) explique la nouvelle garantie en langage produit
- [ ] AIPD : note ajoutée (le rattachement d'une messagerie exige désormais une identité PSC vérifiée et liée au compte)

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis le client mobile
  (`cd Client/Mobile && npm start`) ou Blazor.
- **Cas nominal** : se connecter via Keycloak + PSC, rattacher sa messagerie. **Attendu** :
  rattachement accepté comme avant, boîte ouverte, aucune régression visible.
- **Jeton forgé** : rejouer l'appel de rattachement en ligne de commande avec un jeton PSC
  non signé (copier le jeton réel, en modifier la charge utile — par exemple le `sub` — et
  laisser la signature d'origine, ou signer avec une clé quelconque) :
  ```bash
  curl -sk -X POST https://localhost:{port}/api/v1/account/mailboxes \
    -H "Authorization: Bearer {bearer keycloak}" \
    -H "X-PSC-Token: {jeton forgé}" \
    -H "Content-Type: application/json" \
    -d '{"email":"{adresse mssante}"}' -i
  ```
  **Attendu** : `401`, corps `application/problem+json`, code dédié, **aucune ligne** créée dans
  `mss_accounts` (`docker exec postgres-pgvector psql -U postgres -d mss_registry -c "select count(*) from mss_accounts;"` inchangé).
- **Identité non liée** (mode strict) : avec un jeton PSC **valide** d'un autre professionnel
  de test que celui du compte Keycloak connecté. **Attendu** : `409`, titre « Identité non
  concordante », rien de persisté, trace `MailboxAttached` en échec visible dans l'écran
  d'audit du praticien.
- **Mode observation** : même scénario avec `Enforce=false`. **Attendu** : la requête passe, une
  ligne d'avertissement dans Seq porte les identifiants tronqués, **jamais** le jeton.
- **Banc** : `aspire run` en profil loadtest, tir k6 court. **Attendu** : aucun 401 nouveau.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — durcissement du socle d'identité
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient lue ni écrite ; l'US porte sur des identifiants de compte et de professionnel
- **Authentification PS** : **c'est l'objet de l'US.** Pro Santé Connect, niveau eIDAS substantiel, exigé pour rattacher ; le jeton PSC devient une preuve **vérifiée** au lieu d'une déclaration, et il doit désigner le professionnel du compte connecté (PGSSI-S — référentiel d'authentification, exigence de non-usurpation)
- **Habilitations** : resserrées. Le RPPS (`SubjectNameID`) enregistré au rattachement provient désormais d'un jeton dont la signature est vérifiée
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : rattachement refusé pour identité non concordante (trace `MailboxAttached` en échec) ; jeton PSC invalide (journal technique, sans le jeton). Conservation alignée sur le journal d'audit existant
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé, aucune donnée nouvelle
- **AIPD / impact RGPD** : à mettre à jour — mesure de sécurité nouvelle sur le rattachement (mention à ajouter au registre des mesures)
