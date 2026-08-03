# task-221 — suspendu à l'étape prévue : `kubectl apply` = acte humain

> Pas un échec — c'est la pause consignée à la décision `/start` du 2026-08-03 :
> la forge a livré les fichiers et le câblage (commit api-mail `020e99a`,
> manifests dans `DevOps/Staging` non commités — git DevOps à toi), et 6 items
> du DOD exigent le cluster. Quand tu as fait les gestes ci-dessous, dis-le
> (« cluster prêt, IP du nœud = X ») et je reprends : vérifications cluster,
> smoke comparatif, puis `/forge-simplify` → `/sonar` → `/review`.

## Les gestes qui t'appartiennent

1. **NFS** : créer `/data/loadtest-mail` sur `192.168.0.7` (le PV le référence).
2. **Contrôle puis apply** (les manifests sont dans ton arbre DevOps, non commités —
   relis-les / committe-les à ta convenance) :
   ```bash
   kubectl apply -k DevOps/Staging --dry-run=client   # item 1 du DOD
   kubectl apply -k DevOps/Staging
   kubectl -n healthplatform get pods,pvc             # 3 pods Ready, PVC Bound (item 2)
   ```
3. **Me donner** : l'IP du nœud (pour `MSS_LOADTEST_MAIL_HOST` / `--mail-host`)
   et, si tu l'as sous la main, le RTT poste ↔ cluster (`ping <ip-noeud>`) —
   sinon je le mesurerai à la reprise.

## Ce que je ferai à la reprise (le banc reste local côté SUT)

- RTT mesuré → seed `--latency 100−RTT`, les deux consignés (item 3)
- `MSS_LOADTEST_MAIL_HOST=<ip> dotnet run --project src/AppHost --launch-profile https-load-test`
  (zéro conteneur mail local — déjà prouvé à vide)
- Seed 20 × 50 `--mail-host <ip>` : `read-back verified`, injection directe
  chronométrée vs banc local (item 4)
- Tir smoke `folders` vert contre le cluster ; `enrich` non court-circuité (item 5)
- `kubectl -n healthplatform exec statefulset/loadtest-dovecot -- doveadm who`
  pendant le tir (item 6)
- **Smoke comparatif local vs cluster** (`folders_cold`, `enrich` 10 UIDs,
  lecture froide) → verdict NFS ; si dégradation > ~2× sur les chemins IMAP,
  je m'arrête et je te pose la question du stockage local-path (item 7)

## État des lieux

- api-mail : `feat/task-221-serveurs-mail-cluster`, commit `020e99a` pushé,
  build + 3 285 tests verts
- DevOps (ton repo) : `Staging/kustomization.yaml`,
  `Staging/persistentvolumes/pv-nfs-loadtest.yaml`,
  `Staging/LoadtestMail/{dovecot,greenmail,toxiproxy}.yaml` — non commités
- Skill `loadtest-skill` : section « Mode DISTANT » ajoutée (plan de contrôle)
- ⚠️ `kubectl` est refusé par les permissions de ma session — si tu veux que je
  fasse les dry-run/contrôles moi-même à la reprise, autorise `kubectl` (sinon
  je te demanderai les sorties).
