# todo-task-327.md — Le serveur de messagerie est authentifié avant de recevoir le jeton PSC : chaîne IGC Santé, nom d'hôte et révocation signée

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — une interception sur le chemin réseau (DNS, Wi-Fi de cabinet, proxy) récupère le **jeton PSC XOAUTH2** du praticien et peut le rejouer sur le vrai serveur MSSanté.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-02** — contre-vérifié — et **AUD-03**).

## Ce qui est établi (develop @ `14d58398`)

**Validation TLS (AUD-02)** — `src/Application/Helpers/TlsCertificateValidationSession.cs:78-107`,
`CertificateValidator.cs:27-41, 165-190`, appelants `ImapClientTlsConfigurer.cs:38`,
`SmtpConnectionFactory.cs:292`, `BackgroundImapService.cs:434` :
- pour les domaines OAuth2 (`acceptWhenNoPolicyErrors: false`), `SslPolicyErrors errors` n'est
  **jamais refusé** : `RemoteCertificateChainErrors` et `RemoteCertificateNameMismatch` passent ;
- `ValidatePreHandshake` se limite à `IssuerName.Name?.ToUpper().Contains("IGC-SANTE")` et
  `NotAfter < UtcNow` (`NotBefore` non vérifié) ;
- aucun `X509Chain`, aucun `.Verify(`, aucune vérification de nom d'hôte dans le dépôt.

**Révocation (AUD-03)** — `OcspValidationService.cs:88-96, 149-172, 352-374`,
`CrlValidationService.cs:88-114, 247-254` :
- la signature de la réponse OCSP (`BasicOcspResp`) n'est jamais vérifiée, ni celle de la CRL ;
- URL OCSP, URL CRL et certificat émetteur (AIA) sont lus **dans le certificat du pair** ;
- cache Redis `ocsp:validation:v2:{SerialNumber}` : sans l'émetteur dans la clé.

**Scénarios** : certificat auto-signé dont le DN émetteur contient « IGC-SANTE » accepté ; vrai
certificat IGC Santé d'un **autre hôte** accepté ; réponse OCSP « good » forgée (HTTP clair) ; CRL vide
servie après blocage de l'OCSP ; certificat forgé reprenant le numéro de série public du vrai serveur
qui hérite de son « good » en cache.

## Objective

Qu'une connexion IMAP ou SMTP vers un serveur MSSanté n'envoie **jamais** d'identifiant (jeton PSC ou
mot de passe) avant que le serveur soit authentifié : chaîne construite jusqu'à une autorité IGC Santé
embarquée, nom d'hôte conforme, certificat dans sa période de validité, statut de révocation obtenu
d'une source **signée** et vérifiée.

### Périmètre

1. **Chaîne** : construction contre les ancres IGC Santé **embarquées** (`X509ChainPolicy.CustomTrustStore`,
   `TrustMode = CustomRootTrust`), jamais contre le magasin système ; refus si la chaîne n'aboutit pas.
2. **Nom d'hôte** : `RemoteCertificateNameMismatch` refusé ; vérification explicite si la
   configuration force l'IPv4 (l'hôte attendu reste le nom configuré, pas l'adresse).
3. **Période** : `NotBefore` et `NotAfter` vérifiés.
4. **Suppression du test par sous-chaîne** sur le DN émetteur.
5. **OCSP** : signature vérifiée (émetteur de confiance, ou répondeur délégué portant l'EKU OCSPSigning
   et lui-même chaîné) ; `CertID` rapproché du certificat ; `thisUpdate`/`nextUpdate` contrôlés.
6. **CRL** : signature vérifiée contre l'émetteur de confiance, émetteur de la CRL rapproché.
7. **Cache** : clé = (empreinte de l'émetteur, numéro de série).
8. **Posture d'indisponibilité inchangée** : l'« Option C hybride 4 h » (task-069) reste la règle quand
   la révocation est indisponible — ce qui change, c'est qu'une réponse non signée n'est plus une réponse.
9. Le mode banc (`SslTls:AllowUntrustedCertificates=true`, profil loadtest) reste possible **et journalisé**, jamais actif par défaut.

### Hors périmètre

- La vérification de signature du jeton PSC lui-même (audit E016 du 2026-09-16).
- Le pinning de certificats par opérateur.

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log du run rouge dans le task file) : sur le code actuel, sont **acceptés** —
      (a) un certificat auto-signé dont le DN émetteur contient « IGC-SANTE », (b) un certificat valide
      émis pour un autre nom d'hôte ; après correctif, **refusés** avant tout `AUTHENTICATE`
- [ ] Test : certificat dont `NotBefore` est dans le futur → refusé
- [ ] Test : chaîne jusqu'à une ancre IGC Santé de test embarquée → acceptée (chemin nominal)
- [ ] Test : réponse OCSP « good » **non signée** ou signée par une clé tierce → traitée comme indisponible (pas comme « good »)
- [ ] Test : CRL non signée par l'émetteur → rejetée
- [ ] Test : deux certificats de **même numéro de série** et d'émetteurs différents → entrées de cache distinctes
- [ ] Test d'intégration : `MinimalTlsImapServer` (déjà présent dans `mss.mail.integration.tests`) présentant
      un certificat hors chaîne → la connexion échoue **et aucune commande AUTHENTICATE n'est reçue** par le serveur
- [ ] Non-régression task-069 : posture 4 h sur révocation indisponible, refus immédiat sur révoqué — tests existants verts
- [ ] Refus TLS rendu **503** (`ProblemDetails`, règle 12), message sans détail de certificat ni e-mail
- [ ] Événement de refus TLS journalisé (serveur, motif) sans donnée de santé
- [ ] Banc de charge : le profil loadtest fonctionne toujours (`AllowUntrustedCertificates` journalisé au démarrage)

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil par défaut) ; ouvrir la boîte depuis
   `client-mobile` (`cd Client/Mobile && npm start`) sur un compte MSSanté de formation → la boîte s'ouvre.
2. Interception simulée : pointer (fichier `hosts` du poste) le nom du serveur IMAP de formation vers
   un serveur TLS local présentant un certificat auto-signé « CN=imap, O=IGC-SANTE » → **Attendu** :
   503 « serveur de messagerie non authentifié », et le serveur local **ne reçoit aucun AUTHENTICATE**.
   Avant correctif : l'authentification est envoyée.
3. Même test avec un certificat IGC Santé valide d'un autre hôte (si disponible en formation) → refus.
4. Couper l'accès OCSP (pare-feu local) → comportement task-069 inchangé (grâce 4 h sur cache, Warning journalisé).
5. Profil de banc (`https-load-test`) → les connexions au banc fonctionnent, un avertissement au démarrage signale le mode non sécurisé.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — mise en conformité de la couche transport MSSanté
- **Exigences DSR honorées** : conformité MSSanté (référentiel #1 opérateurs : TLS ≥ 1.2, certificats serveur IGC Santé) — non applicable côté DSR fonctionnel
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée ; la US garantit que le **jeton PSC n'est remis qu'au serveur authentifié**
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : refus TLS et révocation dégradée journalisés (serveur, motif), sans e-mail ni donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : IGC Santé (autorités de certification embarquées), RFC 6960 (OCSP), RFC 5280 (CRL)
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé — renforce la confidentialité des échanges existants
