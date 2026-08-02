# todo-task-216.md — Retirer la voie d'écriture IMAP : elle supprime bien l'attente, mais l'envoi est plus lent avec elle que sans

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-215 (la contre-épreuve qui fonde la décision) — voir son
`## Bench log` et son `## Décision`
**Priorité**: **2** — pas d'urgence fonctionnelle (rien n'est cassé), mais une
connexion IMAP par praticien est un coût permanent qu'on paie pour rien, et le
plafond de connexions par boîte imposé par l'opérateur MSSanté n'est pas
éprouvé.

> **Ce n'est pas un revert de dépit.** Le correctif de task-213 fait exactement
> ce qu'il annonçait — c'est mesuré. Ce qu'il ne fait pas, c'est améliorer
> l'expérience du praticien, et il coûte une connexion par praticien.

## Objective

Que `AppendToSentAsync` et `AppendToDraftsAsync` repassent sur la voie de
lecture, et que la seconde connexion IMAP par praticien disparaisse.

## Ce que la mesure établit (task-215, 2026-08-02)

Trois tirs 500 praticiens, mêmes paramètres, protocole
échauffement → purge → tir. Le témoin A neutralise la voie d'écriture.

| | A — témoin | B | C |
|---|---|---|---|
| Attente p95 `AppendToSent` | 4,345 s | **0,005 s** | **0,005 s** |
| **`send` p95** | **7 874 ms** | 10 439 ms | 12 573 ms |
| **`send` moyenne / médiane** | **1,34** | 1,51 | 1,71 |
| Débit plateau | 791,1 req/s | 796,8 req/s | 802,7 req/s |

Le témoin **satisfait les deux critères du DOD de task-213** (p95 < 10 s, ratio
< 2) ; les tirs porteurs du correctif les manquent. Ce que la voie d'écriture
retire au verrou, elle le repaie en ouverture de connexion : la **détention**
d'`AppendToSent` monte de 3,974 s (A) à 4,557 / 5,287 s (B / C).

Le problème d'origine — un envoi sur vingt au-dessus de trente secondes — **n'est
plus reproductible sans le correctif** : les plafonds de banc levés depuis
(Dovecot `service imap` à 8000, `imap-login` high-performance, dossiers
`Sent`/`Drafts`/`Trash` déclarés) ont retiré la contention qui le produisait.
task-213 répondait à une mesure prise sur un banc bridé.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer qu'il faut tout défaire.** L'instrumentation de task-214
  (étiquettes `operation` et `lane`, mesure dans `ImapLockScope`, retrait de
  l'API dupliquée) **reste** — c'est elle qui a permis de trancher, et elle sert
  à toute mesure de verrou ultérieure. Seule la **voie** disparaît.
- **Ne pas présumer que le mécanisme décrit par task-213 était faux.** Il est
  confirmé : sans voie d'écriture, l'archivage attend 4,3 s au p95 derrière les
  lectures. C'est l'arbitrage coût/bénéfice qui bascule, pas le diagnostic.
- **Ne pas présumer que la conclusion vaut en production.** Elle vaut **pour cet
  hôte**, où l'infra du banc partage le CPU des réplicas. Ce qui la rend
  actionnable : les deux termes ont subi ce biais à l'identique, et c'est
  l'écart **entre eux** qui est mesuré. À écrire dans le code, pas seulement ici.
- **Ne pas présumer qu'un interrupteur serait plus prudent.** Il ferait porter à
  la production un chemin non exercé par défaut, donc non testé, pour un gain
  mesuré négatif. Si le besoin revient, la mesure et l'arbitrage sont écrits :
  la voie se re-crée en quelques lignes.

## Contenu attendu

1. `ImapService.WriteLane` et `UserContextInfo.ForWriteLane()` retirés, avec
   `WriteLaneSuffix` et `IsWriteLane` si plus aucun appelant.
2. **La mesure qui a tranché reste dans le code**, en commentaire là où la voie
   vivait : l'arbitrage de task-213 était juste sur le mécanisme et faux sur le
   bilan, et il faut qu'un futur lecteur trouve les deux, pas seulement le
   second. Réserve « pour cet hôte » incluse.
3. `MailProcessingMetrics.LockLaneWrite` : à **conserver** — l'étiquette `lane`
   n'a plus qu'une valeur utilisée, mais la garder documente la question et
   évite un aller-retour si la voie revient. À justifier par écrit dans un sens
   ou dans l'autre.
4. `report.py` : la table « Voie | Acquisitions /s » reste, elle n'affichera
   plus qu'une ligne. Le verdict « Archivage vs reste » doit rester lisible
   quand `AppendToSent` est de nouveau sur la voie de lecture.
5. Les tests de task-213 (`WriteLaneSessionTests`) : ceux qui portent sur la
   voie disparaissent avec elle ; **`CrossTenantOwnershipTests` et le test de
   famille d'opération restent**.

## Hors scope

- L'instrumentation de task-214, dans son intégralité.
- Le défaut Redis synchrone signalé par task-215
  (`ResilientCacheService.TryGet<T>`, repo `sdk`) — US distincte.
- Toute nouvelle tentative de réduire l'attente d'archivage : elle se
  rediscutera sur une mesure, si le besoin réapparaît.

## Definition of Done

- [ ] Build passes (0 erreur) — Tests pass (0 échec)
- [ ] Plus aucune occurrence de `ForWriteLane` dans le code de production
- [ ] Une seule connexion IMAP par praticien : test prouvant que l'archivage et
      la lecture partagent la même clé de session
- [ ] La mesure qui a tranché est **écrite dans le code**, réserve « pour cet
      hôte » comprise
- [ ] Le sort de `LockLaneWrite` est tranché par écrit
- [ ] `CrossTenantOwnershipTests` verte
- [ ] Tests **constatés RED avant le retrait** (preuve dans le `## Develop log`)

### Dû au banc (ne bloque pas la PR, bloque la clôture de l'US)

- [ ] Tir 500 praticiens iso-conditions avec les tirs de task-215 : `send` p95
      **sous 10 s** et ratio **sous 2** — c'est-à-dire reproduire le témoin A
- [ ] Table des voies : plus aucune acquisition sur `write`

## Manual Test Plan

```powershell
cd Api/Mail/src/AppHost
$env:MSS_LOADTEST = "1"
dotnet run
```

```bash
cd Api/Mail/tests/loadtest-k6
./run.sh mixed          # échauffement
./reset-state.sh        # PURGE, APRÈS l'échauffement
USERS=500 VUS=60 MESSAGES_PER_USER=100 SESSION_ROTATION=0.001 \
VU_TAIL_FACTOR=8 RPS=980 DURATION=3m ./run.sh mixed
python report.py <run-id>
```

⚠️ **Lancer aussi l'échantillonneur** (`observe.ps1`) avant le tir — task-215 ne
l'a pas fait et le comptage des sessions IMAP Dovecot lui a manqué. C'est ici
qu'il doit montrer le retour au plancher simple.

**Ce que l'humain doit voir** :
- `send` p95 **sous 10 s**, ratio moyenne/médiane **sous 2** ;
- table « Voie | Acquisitions /s » : ligne `write` **absente** ;
- sessions IMAP Dovecot revenues au plancher d'avant task-213 (~2 500 à 500
  praticiens, contre ~5 000 avec la voie d'écriture).

**Données** : 100 % synthétiques (boîtes `loadtest-*`). Aucune donnée de santé.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — optimisation technique interne.
- **Exigences DSR honorées** : aucune nouvelle. Le retrait **restaure** le
  comportement d'avant task-213, dont MSSanté-2.4 et le chemin d'émission
  n'avaient de toute façon pas la sémantique altérée.
- ⚠️ **Imputabilité** : l'archivage dans le dossier d'envois est la **trace
  métier** de l'émission. Le retrait le remet sur la voie de lecture, où il
  attend — il ne doit **jamais** le rendre « au mieux ». La vérification
  d'archivage effectif reste exigée, comme dans task-213.
- **INS** : non manipulée. **Authentification PS** : inchangée.
- **Habilitations** : le retrait **simplifie** le cloisonnement — une clé de
  session par praticien au lieu de deux. `CrossTenantOwnershipTests` reste la
  garde.
- **Tracé PGSSI-S** : aucun évènement métier touché.
- **Hébergement HDS** : non — banc de charge, données synthétiques.
- **AIPD / impact RGPD** : inchangé.
