# todo-task-039-provision-igc-sante-certs.md — Provisionner les certificats IGC-Santé dans l'image `api-mail`

**Repos**: api-mail
**Dependencies**: archived-task-038 (recommandé, pas bloquant)
**Epic**: E009

## Objectif

Compléter le fix applicatif de task-038 par une correction **infrastructure** :
embarquer la chaîne de certificats **IGC-Santé** (racine + AC
intermédiaires) dans le trust store OS de l'image Docker `api-mail` via
`update-ca-certificates`.

### Pourquoi

L'image .NET officielle (`mcr.microsoft.com/dotnet/aspnet:10.0` sur
Debian/Ubuntu) consulte `/etc/ssl/certs/ca-certificates.crt`, qui est
hérité du **Mozilla CA Bundle** et **ne contient pas IGC-Santé** (AC
nationale française non soumise à Mozilla). Conséquence sur Linux : toute
connexion TLS vers un endpoint signé IGC-Santé (`*.mssante.fr`,
`*.esante.gouv.fr`, INS, FHIR-DMP, etc.) retombe avec
`SslPolicyErrors.RemoteCertificateChainErrors` côté .NET, et oblige
chaque consommateur à installer son propre `ServerCertificateValidationCallback`.

Sur Windows dev, Schannel valide nativement la chaîne car le Microsoft
Trusted Root Program distribue IGC-Santé via Windows Update — d'où la
divergence local/déploiement.

Cette task pose une **fondation TLS partagée** au niveau OS : à partir de
là, tout composant du process (`HttpClient` REST, gRPC, `MailKit`
secondaire, futurs SDK ANS/INS) bénéficiera de la chaîne valide sans
code custom.

### Articulation avec task-038

| Couche | Couvert par | Rôle |
|---|---|---|
| Métier (IGC-Santé issuer check, OCSP, CRL) | **task-038** (`ImapClientTlsConfigurer` + `CertificateValidator`) | Source de vérité — vérification de révocation temps réel |
| Infra (chaîne reconnue par l'OS) | **task-039** (cette task) | Defense-in-depth — couvre tous les usages TLS du process |

Les deux sont **complémentaires**, pas redondants. task-038 reste la
source de vérité de la validation métier. task-039 réduit la surface
d'erreur OS-level et simplifie les logs.

## Certificats fournis par l'humain

Les fichiers sont déjà déposés dans `Api/Mail/src/Api/Certs/`
(emplacement choisi par le humain ; à conserver tel quel, le Dockerfile
COPY depuis cet emplacement).

| Fichier | Format | Rôle | Chaîne couverte |
|---|---|---|---|
| `ACR-EL.cer` | DER (~1580 B) | **AC Racine IGC-Santé Éléments** — auto-signée | Racine de la chaîne TLS serveur MSSanté |
| `ACI-EL-ORG.cer` | DER (~1856 B) | **AC Intermédiaire IGC-Santé Éléments Organisations** | Signe les certs `*.mssante.fr`, `*.esante.gouv.fr` |
| `ACR-FO.cer` | DER (~1566 B) | **AC Racine IGC-Santé Forte** — auto-signée | Racine pour les CPS (personnes physiques) |
| `ACI-FO-PP.cer` | DER (~1829 B) | **AC Intermédiaire IGC-Santé Forte Personnes Physiques** | Signe les CPS, utile pour mTLS PSC / validation signatures |

**Format** : DER binaire (les 4 fichiers commencent par `30 82 …`).
`update-ca-certificates` exige du PEM avec extension `.crt`. La
conversion DER → PEM est faite **dans le Dockerfile** au moment du build
(les `.cer` source restent identiques à ceux publiés par l'ANS, pour
traçabilité empreinte).

**Couverture** : les 2 premières AC couvrent le besoin immédiat (TLS
serveur MSSanté). Les 2 autres couvrent la validation des CPS et
préparent les usages futurs (PSC mutual TLS, validation de signatures
CDA, etc.). Defense-in-depth complète.

## Scope

### `api-mail` (backend, .NET 10)

- **Fichiers déjà en place** : `Api/Mail/src/Api/Certs/` contient les 4
  `.cer` (ACR-EL, ACI-EL-ORG, ACR-FO, ACI-FO-PP). Ne pas les déplacer.

- **Nouveau `README.md`** dans `Api/Mail/src/Api/Certs/` :
  - Source : https://igc-sante.esante.gouv.fr/
  - Date de téléchargement
  - Empreintes SHA-256 de chaque `.cer` (calculées au build initial)
  - Tableau de couverture (cf. ci-dessus)
  - Procédure de rotation (renouvellement par l'ANS — racine ~20 ans,
    intermédiaires ~5 ans)
  - Pointage vers task-038 pour la couche applicative

- **`Dockerfile`** d'`api-mail` (à identifier — probable
  `Api/Mail/src/Api/Dockerfile`) :

  ```dockerfile
  # Stage final (runtime), avant USER non-root et ENTRYPOINT :
  USER root
  COPY Certs/*.cer /tmp/igc-sante/
  RUN apt-get update \
   && apt-get install -y --no-install-recommends ca-certificates openssl \
   && for f in /tmp/igc-sante/*.cer; do \
        base=$(basename "$f" .cer); \
        openssl x509 -inform DER -in "$f" -out "/usr/local/share/ca-certificates/igc-sante-${base}.crt"; \
      done \
   && update-ca-certificates \
   && openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt \
        /usr/local/share/ca-certificates/igc-sante-ACR-EL.crt \
        /usr/local/share/ca-certificates/igc-sante-ACR-FO.crt \
   && rm -rf /tmp/igc-sante /var/lib/apt/lists/*
  USER app   # ou le user non-root existant
  ```

  Notes :
  - Conversion DER → PEM via `openssl x509 -inform DER -out ...crt`
    (sortie PEM par défaut).
  - Le `openssl verify` en fin de RUN sert de garde-fou build-time : si
    la chaîne ne se monte pas, le build échoue.
  - Si l'image runtime est alpine/distroless (sans `apt`), adapter
    (`apk add ca-certificates openssl` pour alpine, ou multi-stage avec
    un builder Debian qui produit le bundle et COPY dans le runtime
    final).

- **Optionnel — script de vérification runtime**
  `Api/Mail/src/Api/Certs/check-igc-sante-ca.sh` (healthcheck Docker ou
  smoke script) :

  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  for ac in ACR-EL ACR-FO ACI-EL-ORG ACI-FO-PP; do
    test -f "/usr/local/share/ca-certificates/igc-sante-${ac}.crt" \
      || { echo "MISSING: igc-sante-${ac}.crt"; exit 1; }
  done
  grep -q "IGC-SANTE" /etc/ssl/certs/ca-certificates.crt \
    || { echo "IGC-SANTE not in OS bundle"; exit 1; }
  echo "IGC-Santé trust chain OK"
  ```

### Tests

- **Test d'intégration container** (`tests/mss.mail.integration.tests`
  ou nouveau projet `tests/mss.mail.docker.tests`) :
  - Build l'image localement (`docker build`).
  - Lance le container.
  - Exec un `openssl s_client -connect medecin.formation.mssante.fr:993
    -CAfile /etc/ssl/certs/ca-certificates.crt -verify_return_error`
    à l'intérieur du container ; **doit retourner 0**.
  - Skip si Docker daemon indisponible (`[SkippableFact]`).

- **Test alternatif sans Docker** (pour CI sans daemon) :
  - Smoke test : créer un `HttpClient` qui hit
    `https://medecin.formation.mssante.fr/` (ou un endpoint public IGC-Santé)
    et vérifier `response.StatusCode != 0` sans installer de callback custom.
  - Skip si on n'est pas en environnement Linux / si pas de connectivité.

### Documentation

- **`Api/Mail/src/Api/Certs/README.md`** — voir scope ci-dessus.

- **`Api/Mail/README.md`** : section "TLS & certificats" expliquant les
  deux couches (OS bundle via task-039 + `CertificateValidator` via
  task-038) et leurs rôles respectifs.

## Scope OUT

- Pas de modification du code C# (`CertificateValidator`,
  `ImapClientTlsConfigurer` inchangés — task-038 fait toujours autorité
  sur la validation métier).
- Pas de gestion des certificats client (mTLS) — uniquement la chaîne
  serveur (les ACR-FO / ACI-FO-PP sont posés pour validation entrante,
  pas pour configurer un client cert sortant).
- Pas de provisionning du bundle IGC-Santé dans `client-blazor`,
  `client-angular`, `interop-cda`. À traiter dans des tasks séparées si
  besoin.
- Pas d'automatisation de la rotation (téléchargement automatique depuis
  ANS). Manuel pour l'instant — la racine vit ~20 ans, l'intermédiaire
  ~5 ans, c'est gérable à la main.
- Pas de conversion DER → PEM au niveau du repo (les `.cer` restent
  binaires identiques à ceux publiés par l'ANS, pour traçabilité
  empreinte). La conversion se fait dans le Dockerfile.

## Definition of Done

- [ ] `README.md` créé dans `Api/Mail/src/Api/Certs/` documentant les 4
  `.cer`, leur rôle, source ANS, empreintes SHA-256, procédure de
  rotation
- [ ] `Dockerfile` modifié pour `COPY` + conversion DER→PEM +
  `update-ca-certificates` + `openssl verify` build-time
- [ ] Build de l'image réussit (`docker build`)
- [ ] Le container final a bien les 4 certs sous
  `/usr/local/share/ca-certificates/igc-sante-*.crt` et un bundle
  agrégé `/etc/ssl/certs/ca-certificates.crt` contenant "IGC-SANTE"
- [ ] Test d'intégration vert (skippable si pas de Docker / pas de
  connectivité)
- [ ] `Api/Mail/README.md` documente la couche TLS infra
- [ ] PR ouverte avec label `awaiting-human-merge`

## Manual Test Plan

> Validation **obligatoire en déploiement** (la valeur est dans l'image
> tournant en cluster, pas dans le source).

1. Build et push l'image issue de la branche
   `feat/task-039-provision-igc-sante-certs` vers le registry.
2. Déployer sur l'env de dev (`https://weda2-archi.dev.k8s.office.weda.fr/`
   ou équivalent).
3. `kubectl exec -it <pod-api-mail> -- bash` :
   ```bash
   # Vérifier la présence des 4 certs convertis
   ls -la /usr/local/share/ca-certificates/igc-sante-*.crt

   # Vérifier la présence dans le bundle agrégé
   grep -c "IGC-SANTE" /etc/ssl/certs/ca-certificates.crt
   # → attendu : >= 4 occurrences

   # Vérifier la validation de la chaîne IGC-Santé pour le serveur cible
   openssl s_client -connect medecin.formation.mssante.fr:993 \
     -CAfile /etc/ssl/certs/ca-certificates.crt \
     -verify_return_error </dev/null 2>&1 | grep "Verify return code"
   # → attendu : Verify return code: 0 (ok)
   ```

4. Tester `mss-imap-test` exactement comme task-038 (manuel test plan
   identique) — **doit fonctionner même en désactivant temporairement
   `ImapClientTlsConfigurer.Configure`** (preuve que l'OS valide seul).
   ⚠ Remettre `Configure` actif avant le merge : task-038 reste autoritaire.

5. **Test smoke `HttpClient`** : depuis un endpoint debug ou via
   `dotnet-counters`/Seq, déclencher un `HttpClient` `GET` vers
   `https://medecin.formation.mssante.fr/` et vérifier l'absence de
   `HttpRequestException: The remote certificate is invalid`.

**Régression à vérifier** : connexion IMAP nominale (utilisateur avec
`mssEmail` configuré, ouverture messagerie) — comportement identique
au pré-déploiement, logs `CertificateValidator` toujours actifs (pas de
silence).
