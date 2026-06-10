# todo-task-069.md — Perf certificats : suppression du sync-over-async TLS et caches OCSP/CRL/X509

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : optimisation backend pure de la chaîne de validation
> des certificats IGC Santé (TLS IMAP/SMTP, OCSP, CRL). Aucun changement de
> contrat ni d'UI.

## Objective

Éliminer les blocages synchrones (`Task.Run(...).GetAwaiter().GetResult()`)
dans les callbacks de validation de certificats TLS des connexions IMAP/SMTP —
chaque connexion utilisateur subit aujourd'hui 50 à 500 ms de blocage thread
pool pendant le handshake — et mettre en cache les artefacts stables de la
chaîne de validation (certificats émetteurs parsés, réponses OCSP/CRL) avec une
résilience correcte quand les répondeurs sont lents ou indisponibles.

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Application/Services/Implementation/BackgroundImapService.cs:424` | `ValidateAsync(...).GetAwaiter().GetResult()` dans le callback TLS | Élevé |
| 2 | `src/Application/Services/Implementation/SmtpConnectionFactory.cs:221` | `Task.Run(() => ValidateAsync(...)).GetAwaiter().GetResult()` (double anti-pattern) | Élevé |
| 3 | `src/Application/Services/Implementation/ImapConnectionManager.cs:102` | Idem | Élevé |
| 4 | `src/Application/Helpers/ImapClientTlsConfigurer.cs:68` | Idem | Élevé |
| 5 | `src/Application/Services/Implementation/OcspValidationService.cs:193-241` | Le certificat émetteur est caché en `byte[]` mais re-parsé (`LoadCertificate`) à chaque usage | Moyen |
| 6 | `src/Application/Services/Implementation/OcspValidationService.cs:29-97` | Validation OCSP en ligne bloquante si cache Redis indisponible, sans fallback borné | Moyen-Élevé |
| 7 | `src/Application/Services/Implementation/CrlValidationService.cs:125-147` | Téléchargement CRL sans retry/timeout court ni fallback (timeout global 30 s) | Moyen |
| 8 | `src/Application/Services/Implementation/CrlValidationService.cs:130` + `OcspValidationService.cs:76` | Validations séquentielles certificat par certificat, parallélisables | Moyen |

## Comportement attendu

- Les callbacks TLS ne bloquent plus de thread : la validation
  asynchrone (OCSP/CRL) est effectuée **avant** ou **après** le handshake sur un
  chemin async, ou s'appuie sur un cache pré-chargé consultable de façon
  synchrone non bloquante dans le callback.
- Les certificats émetteurs sont cachés sous forme d'objets `X509Certificate2`
  (clé = thumbprint, TTL raisonnable) — plus de re-parse DER par requête.
- OCSP/CRL : timeout court explicite, retry/circuit-breaker, et stratégie de
  fallback documentée et validée (comportement en cas de répondeur injoignable —
  **décision sécurité à arbitrer, voir question ci-dessous**).
- La validation de plusieurs certificats d'un même envoi est parallélisée.

⚠️ **Point d'arbitrage sécurité (à trancher avant implémentation, sinon
`questions/task-069.md`)** : en cas d'indisponibilité du répondeur OCSP/CRL,
le comportement (fail-open avec cache périmé toléré N heures vs fail-close)
doit être validé par l'humain — c'est un compromis PGSSI-S vs disponibilité de
l'Espace de Confiance MSSanté. Le statu quo actuel doit être documenté dans la
PR.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Plus aucun `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` sur la chaîne de validation de certificats (vérifiable par grep sur les 4 fichiers concernés)
- [ ] Cache `X509Certificate2` émetteurs en place (plus de re-parse DER par validation)
- [ ] Timeout explicite <= 5 s + retry borné sur les téléchargements OCSP et CRL
- [ ] Comportement de fallback OCSP/CRL indisponible documenté dans la PR et validé par l'humain
- [ ] Validation multi-certificats parallélisée (`Task.WhenAll` ou équivalent)
- [ ] Unit tests : >= 1 test par branche du nouveau flux de validation (cache hit, cache miss, répondeur down, certificat révoqué)
- [ ] Integration test : envoi SMTP via le pipeline DI complet avec validation de certificat mockée (happy path + certificat révoqué refusé)
- [ ] La sémantique de sécurité est inchangée : un certificat révoqué reste refusé (tests le prouvant)
- [ ] Aucune donnée de santé ni détail de certificat nominatif en clair dans les logs

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Depuis le client Blazor, envoyer un mail MSSanté à une adresse de test : l'envoi
  aboutit, la latence de premier envoi est mesurée puis comparée à un second
  envoi (le second doit être nettement plus rapide grâce aux caches).
- Couper l'accès réseau au répondeur OCSP de test (ou pointer vers une URL
  invalide en configuration) : l'envoi suit le comportement de fallback arbitré
  (et le log serveur trace l'évènement, sans bloquer 30 s).
- Vérifier sous charge légère (10 envois successifs) l'absence de blocage et la
  stabilité du temps de réponse.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique ; les exigences MSSanté existantes (IGC Santé) restent honorées à l'identique
- **Exigences DSR honorées** : MSSanté — vérification de la validité des certificats IGC Santé maintenue (non-régression, pas de nouvelle exigence)
- **INS** : non applicable — aucun traitement patient
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : évènements de validation de certificat (échec, révocation, fallback dégradé) journalisés ; durée de conservation inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé
