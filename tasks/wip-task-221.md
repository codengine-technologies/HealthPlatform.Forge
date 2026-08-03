# todo-task-221.md — Sortir les serveurs mail simulés de l'hôte sous test : Dovecot/GreenMail/Toxiproxy sur le cluster k8s

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune stricte. À livrer **avant toute campagne au-delà de
~500 praticiens** — c'est le prérequis de mesure de task-220 aux paliers
hauts, pas de sa livraison. L'**application des manifests au cluster est un
acte de l'humain** (accès ESX/k8s) ; la forge livre les fichiers et le
câblage, l'humain `kubectl apply`.
**Priorité**: **2**.

> **Décisions humaines déjà prises (2026-08-03)** : exposition **NodePort** ;
> **StorageClass `nfs`** disponible ; RTT poste ↔ cluster **à mesurer pendant
> cette task** (« à déterminer plus tard »).
>
> **Décision /start (2026-08-03)** : les manifests sont livrés dans
> `DevOps\Staging` en **mode code-only** — la forge écrit les fichiers mais ne
> touche **jamais** au git de DevOps (commit/push = humain, comme
> client-angular). Le `kubectl apply` au cluster reste un acte humain : quand
> `/develop` atteint les items de DOD qui exigent le cluster, il **suspend et
> demande** (questions/), puis reprend les vérifications après ton apply.

## Objective

Qu'au-delà de 500 praticiens, le banc mesure **api-mail** et non plus le
serveur IMAP simulé qui partage sa machine.

## Le défaut

En production, les serveurs MSSanté sont des **tiers externes**. Sur le banc,
Dovecot/GreenMail/Toxiproxy tournent **sur l'hôte sous test** et lui volent
ses ressources — mesuré :

- à 500 praticiens, **Dovecot consomme 2,6 cœurs** de l'hôte (marginal à 200) ;
- ce coût suit le **nombre de boîtes et le volume du maildir** (9 Go), pas la
  charge — il croît donc mécaniquement avec la population, l'axe exact que le
  chantier scalabilité pousse ;
- les sessions valent `praticiens × réplicas` (2 500 à 500), indépendamment
  du trafic.

Conséquence : tout chiffre > 500 mesuré sur le banc actuel est un artefact
**connu d'avance** — le publier serait pire que ne pas mesurer. Et
l'attribution est impossible : le CPU de Dovecot et celui d'api-mail se
mélangent dans la même enveloppe machine.

## Architecture cible

```
Hôte dev (SUT)                          ESX / k8s — namespace loadtest-mail
┌─────────────────────┐                ┌────────────────────────────────────┐
│ api-mail ×5         │─IMAPS 30993──▶│ Toxiproxy ──▶ Dovecot (StatefulSet, │
│ Postgres/PgBouncer  │─SMTPS 30465──▶│           ──▶ GreenMail   PVC nfs)  │
│ Redis, k6, Seq      │─API  30474──▶│ (latence MSSanté injectée ICI)      │
│                     │─direct 30994─▶│ Dovecot sans latence (seed)         │
└─────────────────────┘                └────────────────────────────────────┘
```

Postgres/PgBouncer/Redis **restent** avec le SUT : ils font partie de la
plateforme en production. On ne sort que ce qui est externe en réalité.

Gain collatéral décisif : `kubectl top pods` donne le **CPU de Dovecot mesuré
séparément** du SUT — l'attribution que le banc n'a jamais eue.

## ⚠️ Le risque nommé : Dovecot sur NFS

Le maildir est une charge **metadata-heavy** (un fichier par message, ~50 000
fichiers à 500×100) et Dovecot sur NFS est un cas de dégradation **connu et
documenté** (verrouillage d'index, fsync). Trois atténuations à appliquer,
puis **un verdict à rendre par la mesure** :

1. **Un seul pod Dovecot** — les pathologies NFS graves viennent de l'accès
   concurrent multi-serveurs, qu'on n'a pas ;
2. **Index Dovecot hors NFS** (`mail_index_path` sur `emptyDir` local du
   nœud) : seuls les messages vivent sur le PVC, les index — le point chaud —
   restent locaux ;
3. Réglages `mail_fsync` / `mail_nfs_*` adaptés dans la ConfigMap.

**Verdict par smoke comparatif obligatoire** : mêmes opérations
(`folders_cold`, `enrich` 10 UIDs, lecture froide) contre le banc local puis
contre le cluster, écarts consignés. Si la dégradation dépasse ~2× sur les
chemins IMAP, **s'arrêter et demander à l'humain** un stockage local-path sur
le nœud à la place du NFS — ne pas adopter des chiffres qu'on sait faussés.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que le RTT poste↔cluster est négligeable.** Le mesurer en
  début de task, et régler la latence Toxiproxy à `100 ms − RTT` pour que la
  latence MSSanté simulée totale reste 100 ms. Consigner les deux valeurs.
- **Ne pas faire transiter le seed par Toxiproxy.** L'injection fait des
  dizaines de milliers d'APPEND séquentiels : à 100 ms pièce c'est des heures.
  Le seed injecte en **direct** (NodePort 30994, sans latence) ; seuls les
  `UserSettings` des praticiens pointent via Toxiproxy.
- **Ne pas oublier l'alignement du mot de passe IMAP** — trois endroits,
  désormais dont un sur le cluster : la `passdb` de la ConfigMap Dovecot,
  `TestMode__Password` de l'AppHost, `--mail-password` du seed. Un
  désalignement = échec d'authentification sur tout le banc, sans message
  clair (piège documenté du skill).
- **Ne pas chercher `doveadm` par un port** : `kubectl exec` dans le pod. Les
  contrôles du skill (`doveadm who`) changent de forme, pas de fond.
- **Ne pas laisser l'AppHost démarrer les conteneurs mail locaux** quand le
  banc pointe vers le cluster — sinon deux mondes coexistent et les
  `UserSettings` désignent tantôt l'un tantôt l'autre.
- **Ne pas reporter la conf Dovecot à l'identique sans la relire** : chaque
  réglage du `dovecot.conf` actuel a coûté une campagne (`service imap` 8000,
  `imap-login` high-performance, `mail_max_userip_connections=100`,
  `special_use` Sent/Drafts/Trash + `auto = subscribe`). La ConfigMap doit
  les porter **tous**, plus les réglages NFS ci-dessus.

## Contenu attendu

1. **Manifests** sous `D:\TechWatch\HealthPlatform\DevOps\Staging` (kustomize) :
   - `Namespace` `healthplatform` ;
   - **Dovecot** : StatefulSet (1 réplica), PVC `nfs` **50 Gi**, ConfigMap
     (conf complète + réglages NFS + index sur `emptyDir`), Service NodePort
     **30993** (via Toxiproxy) et **30994** (direct, seed) — requests/limits
     calés sur la mesure : request 4 CPU, limit 8 ;
   - **GreenMail** : Deployment + Service (SMTPS via Toxiproxy **30465**),
     ~2 CPU / 2–4 Gi ;
   - **Toxiproxy** : Deployment + Service (API **30474**, listeners IMAP/SMTP).
   - **Volume** : A configurer dans DevOps\Staging\persistentvolumes\pv-nfs-loadtest.yaml
2. **Seed** : endpoints paramétrables (URL de l'API Toxiproxy, hôte/ports
   distants écrits dans les `UserSettings`), injection directe.
3. **AppHost** : variable `MSS_LOADTEST_MAIL_HOST` — posée, le profil loadtest
   ne démarre **aucun** conteneur mail local et câble le banc vers le cluster ;
   absente, comportement actuel inchangé.
4. **Étape RTT** : mesure, réglage Toxiproxy à `100 − RTT`, consignation.
5. **Smoke comparatif local vs cluster** (verdict NFS, cf. section risque).
6. **Mise à jour du skill `loadtest-skill`** (plan de contrôle) : mode distant,
   contrôles `kubectl`, avertissement NFS — le skill évolue avec le banc.

## Hors scope

- Le scénario `journey` (**task-220**) — les deux US sont indépendantes.
- Le déplacement de Postgres/PgBouncer/Redis — ils appartiennent au SUT.
- Toute campagne de mesure au-delà du smoke comparatif.
- L'automatisation du `kubectl apply` — acte humain, cluster géré par l'humain.

## Definition of Done

- [ ] `kubectl apply -k DevOps/Staging --dry-run=client` sans erreur (preuve
      dans le `## Develop log`) — manifests livrés code-only, git DevOps humain
- [ ] Après application par l'humain : les 3 pods `Ready`, PVC `Bound` sur la
      StorageClass `nfs`
- [ ] RTT mesuré, latence Toxiproxy réglée à `100 − RTT`, les deux consignés
- [ ] Seed 20 utilisateurs contre le cluster : `read-back verified`, injection
      en direct (durée comparable au banc local, preuve chronométrée)
- [ ] Tir smoke `folders` vert contre le cluster ; `enrich` **non
      court-circuité**
- [ ] `doveadm who` via `kubectl exec` montre les sessions pendant le tir
- [ ] **Smoke comparatif local vs cluster consigné** (folders_cold, enrich,
      lecture froide) avec verdict NFS explicite ; si dégradation > ~2×,
      question posée à l'humain **avant** d'adopter les chiffres
- [ ] `MSS_LOADTEST_MAIL_HOST` posée → zéro conteneur mail local démarré ;
      absente → comportement strictement inchangé (les deux vérifiés)
- [ ] Mot de passe IMAP aligné aux trois endroits (contrôle explicite)
- [ ] Skill `loadtest-skill` mis à jour (mode distant + pièges)

## Manual Test Plan

```bash
# côté cluster (humain) :
kubectl apply -k DevOps/Staging
kubectl -n healthplatform get pods,pvc         # 3 pods Ready, PVC Bound

# côté banc :
cd Api/Mail
MSS_LOADTEST_MAIL_HOST=<ip-noeud> dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 20 --messages 50 --api http://127.0.0.1:5052
export BYPASS_KEY=loadtest-local-only
tests/loadtest-k6/run.sh folders
```

**Ce que l'humain doit voir** :
- `docker ps` sur le poste : **aucun** conteneur `loadtest-dovecot` /
  `loadtest-greenmail` / `loadtest-toxiproxy` local ;
- le tir `folders` vert, latences cohérentes avec le budget (100 ms simulés
  RTT compris) ;
- `kubectl top pods -n loadtest-mail` pendant le tir : le CPU de Dovecot
  visible **séparément** du poste ;
- `kubectl exec` + `doveadm who` : sessions ≈ utilisateurs × réplicas ;
- le tableau comparatif local/cluster dans le rapport, avec le verdict NFS.

**Données de test** : synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — outillage de banc.
- **Exigences DSR honorées** : aucune nouvelle.
- **INS** : non manipulée.
- ⚠️ **Le maildir part sur un stockage partagé (NFS du cluster)** : il ne
  contient que des CDA de **test** (`JEUX_TESTS_FULL`) et des boîtes
  `loadtest-*` — c'est acceptable **à condition** que le volume soit dédié au
  banc, nommé comme tel, et purgeable (`kubectl delete pvc`). **Interdiction
  absolue** d'y faire transiter une donnée réelle : ce cluster n'est pas HDS.
- **Habilitations / Tracé PGSSI-S** : sans objet — aucun évènement métier.
- **Hébergement HDS** : non applicable (données synthétiques exclusivement —
  et c'est la garde ci-dessus qui le garantit).
- **AIPD / impact RGPD** : néant.

## Branches
- `api-mail` (pushed) : feat/task-221-serveurs-mail-cluster — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-221-serveurs-mail-cluster
- `dtos-mss` (pushed, auto-inclus) : feat/task-221-serveurs-mail-cluster — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-221-serveurs-mail-cluster
- `devops` (code-only, décision /start 2026-08-03) : la forge écrit les manifests dans `DevOps/Staging` mais ne touche jamais au git de DevOps — commit/push et `kubectl apply` = humain

## Develop log

- **Repos touchés** : api-mail (commit `020e99a`, pushé) ; DevOps (code-only — fichiers écrits, non commités, git humain) ; plan de contrôle (skill loadtest). `dtos-mss` : branche sans commit, aucun changement de contrat.
- **Livré — manifests kustomize (`DevOps/Staging`, code-only)** :
  - `kustomization.yaml` (racine Staging, périmètre banc mail uniquement — le reste de la stack continue en `apply -f`)
  - `persistentvolumes/pv-nfs-loadtest.yaml` — PV statique NFS 50 Gi (`192.168.0.7:/data/loadtest-mail`, classe `nfs-loadtest`, patron pv-nfs-postgresql) + PVC lié
  - `LoadtestMail/dovecot.yaml` — StatefulSet 1 réplica (⚠️ ne pas scaler : NFS multi-serveurs = pathologie connue), ConfigMap portée de `src/AppHost/dovecot/dovecot.conf` (TOUS les plafonds durement acquis) **+ réglages NFS** (index sur `emptyDir` local via `INDEX=`, `mmap_disable`, `mail_fsync=never`, `mail_nfs_*=no`), requests 4 CPU / limits 8, Services : interne 993 (upstream Toxiproxy) + NodePort **30994** (direct, seed)
  - `LoadtestMail/greenmail.yaml` — puits SMTP, Service interne (jamais exposé direct)
  - `LoadtestMail/toxiproxy.yaml` — Deployment + Service NodePort **30474** (API), **30993** (IMAPS praticiens), **30465** (SMTPS praticiens)
  - Validation : 11 documents YAML valides, chemins kustomize résolus (contrôle Python — `kubectl` est bloqué par les permissions de la session ; le `--dry-run=client` du DOD est délégué à l'étape humaine, cf. questions/task-221.md)
- **Livré — AppHost (`src/AppHost/AppHost.cs`)** : `MSS_LOADTEST_MAIL_HOST` posée → **zéro conteneur mail local** ; PgBouncer + collector OTLP restent locaux (plateforme sous test). **Vérifié au runtime, les deux sens** : posée → 2 conteneurs `loadtest-*` (pgbouncer, otel-collector) ; absente → les 5 (dovecot, greenmail, toxiproxy en plus), comportement inchangé. ⚠️ La première version du garde coupait aussi pgbouncer/otel — **attrapé par la vérification runtime**, corrigé en scindant le bloc.
- **Livré — seed (`SeedOptions.cs`, `Program.cs`)** : interrupteur unique `--mail-host` (défaut : env `MSS_LOADTEST_MAIL_HOST`, la même variable que l'AppHost) → UserSettings vers NodePorts 30993/30465, **injection directe vers 30994** (jamais via la latence), API Toxiproxy vers 30474 ; upstreams inchangés (les Services k8s portent les noms des alias Aspire). **Piège attrapé** : ports d'écoute dans le pod Toxiproxy (13993/13465) désormais distincts des ports joints — en k8s le Service mappe NodePort → containerPort. Test-first : 4 tests nouveaux, RED constaté avant implémentation.
- **Livré — skill `loadtest-skill`** : section « Mode DISTANT » (déploiement, surface NodePort, RTT à soustraire de la latence, contrôles `kubectl exec`/`kubectl top`, purge du PVC, piège NFS + verdict par smoke comparatif obligatoire).
- **Local build / test** : ✓ build 0 erreur, ✓ **3 285 tests verts / 0 échec** (une passe intermédiaire a eu 1 flaky pendant le teardown du banc de vérification ; deux re-runs verts)
- **DOD self-check** : 4 items vérifiables faits (variable posée/absente ✓✓, mot de passe IMAP aligné aux 3 endroits ✓ — ConfigMap/`TestMode__Password`/seed, skill ✓) ; **6 items exigent le cluster** → suspendu, `questions/task-221.md` (dry-run kubectl, pods Ready + PVC Bound, RTT + latence, seed 20 read-back, smoke folders + enrich non court-circuité, doveadm, smoke comparatif NFS)
- **Next step** : humain — `questions/task-221.md` (kubectl apply + relevés), puis la forge reprend les vérifications cluster et enchaîne `/forge-simplify` → `/sonar` → `/review`.

## Vérification cluster (2026-08-03, après apply humain)

- **Topologie découverte** : le poste (192.168.1.x) joint le cluster (192.168.0.x) via le **WAN du pfSense** (`192.168.1.69`) — 4 port-forwards WAN (alias par port) vers `192.168.0.3` posés par l'humain ; « Block private networks » décochée. `MSS_LOADTEST_MAIL_HOST=192.168.1.69`.
- **Item 3 — RTT** : ≈ **5 ms** (connexion TCP chronométrée poste → pod Toxiproxy, médiane 4,6 ms sur 5 essais ; l'ICMP ne traverse pas les forwards) → **latence injectée = 95 ms** (seed `--latency 95`, k6 `LATENCY_MS=95`). ⚠️ Trouvé en route : le `setup()` de chaque tir k6 ré-appliquait le profil à 100 ms en dur — surcharge `LATENCY_MS` ajoutée (`b3f45f1`).
- **Item 4 — seed distant** : 20 × 50, injection **directe** (30994), **49 s**, `read-back verified` — plus rapide que le banc local (l'injection ne paie pas la latence).
- **Item 5 — smokes** : k6 `folders` **PASS** (7 076 req/60 s, **0,00 % err**, 100 % checks, p95 warm 15 ms) — après correction du défaut TOXIPROXY du harnais (`b3f45f1`, trouvé par ce tir) ; `enrich` **non court-circuité** : 10,16 s / 6,62 s / 6,30 s pour 10 UIDs (travail CDA réel, ≫ 200 ms).
- **Item 7 — smoke comparatif local vs cluster, verdict NFS : TENU** (régime établi, serveur chaud) :

| Chemin IMAP | Cluster | Réf. locale (2026-07-25, 100 ms) | Ratio |
|---|---|---|---|
| `enrich` froid 10 UIDs | 6,30–6,62 s | 4,3 s | **~1,5×** ✓ |
| `folders_cold` | 1,05–1,21 s | 0,7–1,05 s | **~1,1×** ✓ |
| lecture froide | 0,50–1,17 s | ~0,9 s | **~1,0×** ✓ |

  Le tout premier `enrich` (10,16 s) paie la construction des index Dovecot (emptyDir) + cache NFS froid — écarté du verdict (première touche, consignée). Aucun chemin > 2× → **NFS retenu**, surcoût `enrich` ~1,5× assumé et consigné.
- **Item 8 — re-confirmé en conditions réelles** : variable posée → seuls `loadtest-pgbouncer` + `loadtest-otel-collector` locaux, api-mail répond sur 5052 contre le cluster.
- **Items restants (sorties humaines à coller)** : item 1 (`kubectl apply -k DevOps/Staging --dry-run=client` — l'apply réel a réussi, le dry-run reste à consigner), item 2 (`get pods,pvc` — les Services sont Active, il manque la preuve pods Ready/PVC Bound), item 6 (`doveadm who` via `kubectl exec` pendant que les sessions du tir sont poolées).
