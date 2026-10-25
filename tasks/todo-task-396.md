# todo-task-396.md — Révocation IMAP sans dépendre du serveur IGC-Santé, et panne identifiable

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Priorité**: **1** — le 2026-10-25, l'arrêt de `igc-sante.esante.gouv.fr` a rendu la messagerie
inutilisable en formation (500 sur les routes de la boîte de réception) dès l'expiration des caches.
Le même défaut existe en production pour toute autorité absente de la graine.

> **Périmètre backend seul (justification).** Le défaut et sa correction sont dans la validation du
> certificat du serveur IMAP. Aucun écran ne change : les clients reçoivent un 503 au lieu d'un
> 500, et le traitent déjà comme une erreur de service. Aucun parcours médecin n'est créé ni
> modifié, donc il n'y a pas de scénario au catalogue. `/e2e` rejoue quand même les voies, puisque
> la task touche `api-mail`.

## Constat (Seq local, 2026-10-25)

Sur `GET /api/v1/mail/folders/INBOX/emails/today` et `.../unread/today` : **500 après ~21 s**,
avec cette séquence :

```
[IsCertificateFromIgcSante] issuerName=CN=TEST AC IGC-SANTE ELEMENTAIRE ORGANISATIONS, OU=IGC-SANTE TEST, …
[ValidateRevocation] OCSP validation failed, falling back to CRL. Errors: Failed to download issuer certificate. TaskCanceledException
[ValidateRevocation] CRL validation also failed. Errors: Failed to obtain CRL
[PerformConnectAndAuthenticateAsync] Server certificate validation failed: Certificate revocation check failed (OCSP and CRL)
Result-mapped 500 … (ResultStatus=Error)
```

- Le serveur IMAP de formation (`mail-psc.formation.mailiz.mssante.fr`) est signé par
  **`TEST AC IGC-SANTE ELEMENTAIRE ORGANISATIONS`**.
- Pour construire la requête OCSP, `OcspValidationService` a besoin du certificat de cet émetteur.
  La graine embarquée (task-288, `src/Application/Resources/IssuerCertificates/`) ne contient que
  les **quatre AC de production**. L'émetteur est donc téléchargé via l'AIA
  `http://igc-sante.esante.gouv.fr/AC%20TEST/ACI-EL-ORG-TEST.cer`, et ce serveur ne répond plus.
- Le repli sur la CRL échoue pour la même raison : la CRL
  (`http://igc-sante.esante.gouv.fr/CRL/ACI-EL-ORG-TEST.crl`) est hébergée sur ce même serveur.
- **Le répondeur OCSP, lui, fonctionnait.** `openssl ocsp` vers `http://ocsp.esante.gouv.fr`, avec
  l'émetteur fourni à la main, rend `good` (This Update 2026-10-24 23:01, Next Update 2026-10-30).
  Le seul maillon manquant était la copie locale de l'émetteur.
- **La panne n'est pas identifiable.** L'erreur rendue est un 500 générique. Le log
  `Failed to download issuer certificate. TaskCanceledException` ne nomme ni l'URL, ni l'hôte, ni
  la durée. Rien ne dit que c'est une autorité IGC-Santé injoignable, et non le serveur MSSanté.

**Contournement local en place** (à retirer par cette task) : l'intermédiaire TEST a été déposé
dans la graine sous `local-contournement-ACI-EL-ORG-TEST.cer`. Le fichier est exclu de git par
`.git/info/exclude` dans `Api/Mail` et prend effet au redémarrage de l'AppHost.

## Objective

1. La vérification de révocation du serveur IMAP **ne dépend plus** du serveur de publication de
   l'IGC-Santé pour les autorités connues, qu'elles soient de production ou de TEST. Seul le
   répondeur OCSP reste nécessaire.
2. Quand la révocation ne peut vraiment pas être vérifiée (OCSP et CRL injoignables), api-mail
   **reste fermé**, comme aujourd'hui. Mais il le dit clairement :
   - un **503** typé au lieu d'un 500 ;
   - un log `Error` unique qui nomme l'autorité, chaque point d'accès tenté (OCSP, AIA, CRL), son
     motif et sa durée.

## Definition of Done

- [ ] Les autorités IGC-Santé **TEST** sont ajoutées à la graine :
      - au minimum `TEST AC IGC-SANTE ELEMENTAIRE ORGANISATIONS` ;
      - les homologues TEST des trois autres AC déjà présentes (FORT PERSONNES, RACINE
        ELEMENTAIRE, RACINE FORT), si elles sont disponibles.

      Leur provenance et leur empreinte SHA-256 sont documentées dans le README de
      `Resources/IssuerCertificates/`.
- [ ] Le contournement local est retiré :
      - le fichier `local-contournement-ACI-EL-ORG-TEST.cer` ;
      - sa ligne et son commentaire dans `Api/Mail/.git/info/exclude`.
- [ ] Test unitaire : un certificat serveur émis par `TEST AC IGC-SANTE ELEMENTAIRE ORGANISATIONS`
      est résolu par la graine, **sans appel réseau** (coordinateur de téléchargement jamais
      sollicité). Vu rouge sans le `.cer` TEST.
- [ ] Révocation impossible (OCSP et CRL en échec, pas de cache utilisable) → `Result.Unavailable`
      propagé jusqu'au contrôleur → **503** `application/problem+json`, via `ResultModelExtensions`
      et le pipeline RFC 7807 (règle 12), plus jamais 500.
- [ ] Le `detail` de ce 503 dit que la vérification de sécurité du serveur de messagerie est
      momentanément impossible. Il ne contient ni URL, ni nom d'hôte, ni message d'exception brut.
- [ ] **Test d'intégration de bout en bout** : une route de la boîte de réception
      (`GET /api/v1/mail/folders/INBOX/emails/today`) avec les points d'accès de révocation
      simulés injoignables (fournisseurs externes : OCSP, AIA, CRL) → 503 + ProblemDetails, lu
      dans la réponse réelle. Vu rouge sur le code actuel, qui rend 500 (règle 1b). La preuve est
      consignée dans le `## Develop log`.
- [ ] Test d'intégration de non-régression : un certificat **révoqué** (OCSP `revoked`) reste
      refusé immédiatement, sans grâce ni repli.
- [ ] Un seul log `Error` par vérification impossible, qui nomme l'émetteur et, pour chaque point
      d'accès tenté (OCSP, AIA, CRL) : l'URL, le motif (délai dépassé, refus, statut HTTP, réponse
      illisible) et la durée. Test unitaire sur le contenu du log.
- [ ] Le log de téléchargement de l'émetteur (`Failed to download issuer certificate`) nomme l'URL
      et la durée.
- [ ] Aucune donnée de santé ni identifiant de boîte dans ces logs, en dehors du contexte de requête
      déjà présent.
- [ ] Build passe (0 erreur) ; tests passent (0 échec) ; `/e2e` vert.

## Manual Test Plan

1. **Préparer la panne.** Rendre `igc-sante.esante.gouv.fr` injoignable sur le poste, en
   PowerShell administrateur :
   `Add-Content C:\Windows\System32\drivers\etc\hosts "192.0.2.1 igc-sante.esante.gouv.fr"`
   (TEST-NET-1 : paquets jetés). Si le serveur est réellement en panne, cette étape est inutile.
2. **Vider les caches de révocation.** Supprimer les clés `ocsp:*` et `crl:*` du Redis de
   l'AppHost (Redis Commander du tableau de bord Aspire), puis relancer l'AppHost
   (`dotnet run --project Api/Mail/src/AppHost`). Ce redémarrage vide aussi le cache en mémoire.
3. **Nominal malgré la panne.** Ouvrir weda2 ou le client mobile avec le compte de formation
   (`…@medecin.formation.mssante.fr`), puis ouvrir la boîte de réception.
   - **Attendu** : la liste s'affiche dans un délai normal.
   - Dans Seq : `Issuer certificate resolved from the embedded seed for … TEST AC IGC-SANTE
     ELEMENTAIRE ORGANISATIONS`, puis une validation OCSP réussie. Aucun `Failed to download
     issuer certificate`.
4. **Révocation vraiment impossible.** Ajouter aussi `192.0.2.1 ocsp.esante.gouv.fr` au fichier
   hosts, refaire l'étape 2, puis ouvrir la boîte de réception.
   - **Attendu** : la réponse de l'API est `503` + ProblemDetails, sans URL dans le `detail`.
   - Dans Seq : **une** entrée `Error` qui nomme l'émetteur et les points d'accès OCSP et CRL, avec
     le motif « délai dépassé » et leurs durées.
5. **Remise en état.** Retirer les lignes ajoutées au fichier hosts.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — robustesse de la sécurité du canal MSSanté
- **Exigences DSR honorées** : vérification de révocation du certificat serveur de l'opérateur
  MSSanté **maintenue et obligatoire**. La politique reste fermée : pas de connexion si la
  révocation ne peut pas être vérifiée et qu'aucun cache n'est utilisable (grâce de task-069
  inchangée). Un certificat révoqué reste refusé sans délai.
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : le refus pour révocation invérifiable est tracé avec son motif (autorité et
  points d'accès injoignables). Le chiffrement et l'authentification du canal ne sont pas affaiblis.
- **Consentement patient** : non applicable
- **Référentiels métier** : IGC-Santé (AC de production et de TEST, certificats publics de l'ANS)
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle nouvelle dans les logs

## Notes de cadrage

- **Pourquoi embarquer les AC TEST dans tous les environnements.** La graine ne sert qu'à
  **trouver l'émetteur** pour construire la requête OCSP. Elle ne décide pas de la confiance. Un
  certificat TEST présenté en production ne devient donc pas plus acceptable parce que son
  émetteur est dans la graine. Une graine par environnement ajouterait une configuration à tenir
  sans gain de sécurité.
- **Constat annexe, hors périmètre** : `IsCertificateFromIgcSante` accepte tout émetteur dont le
  nom contient `IGC-SANTE`, donc aussi les AC **TEST** en production. Faut-il refuser les AC TEST
  hors formation et recette ? C'est une décision de sécurité, à instruire dans une US dédiée.
- **Le proxy PSC souffre de la même panne** (même jour, même serveur AIA, côté mTLS sortant).
  Elle est traitée dans le dépôt `psc-auth-proxy` par sa task-018.
