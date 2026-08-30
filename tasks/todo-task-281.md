# todo-task-281.md — Lire ses dossiers ne fait plus la queue derrière l'archivage de ses envois

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

**La lecture de dossier du médecin attend derrière l'archivage de ses propres
messages envoyés.** C'est établi, chiffré, et c'est la première fois.

Le tir du 2026-08-30
(`Api/Mail/tests/loadtest-k6/reports/2026-08-30/report-journey-500-lot277279-20260830-180647.md`,
finding **F-LOCK-1**), grâce à l'étiquette `holder` livrée par task-278 et
conservée à son retrait :

| Attente sur `imap_session` | p95 médian | max |
|---|---|---|
| **`ReadFolder` derrière `AppendToSent`** | **3,938 s** | **20,357 s** |
| `ReadFolder` derrière `UpdateFlag` | 0,638 s | 0,725 |
| `UpdateFlag` derrière `GetAttachmentStream` | 0,498 s | 0,875 |
| `ReadFolder` derrière `ReadFolder` | 0,487 s | 28,000 |
| **`ReadFolder` derrière rien (`(none)`)** | **0,005 s** | 0,005 |

**La dernière ligne est la contre-épreuve** : verrou libre, l'acquisition ne coûte
rien. L'attente est donc de la **contention pure**, pas un coût d'acquisition —
deux situations aux remèdes opposés, que le rapport ne distinguait pas avant.

### Pourquoi ça a mis trois US à se voir

`ReadFolder` attendait **82,8 ms en moyenne** au tir du 29/08 (~48 % du temps
serveur de la route). task-276, task-277 et task-278 ont toutes buté dessus sans
pouvoir l'attribuer : l'histogramme disait *qui attend*, jamais *derrière qui*.
task-276 a même publié une cause **fausse** sur ce chiffre, réfutée par sa propre
correction d'instrument.

### Ce que task-272 avait déjà fait, et ce qu'il reste

task-272 a sorti l'archivage du **chemin de la réponse** : l'acquittement de
l'envoi n'attend plus la copie dans « Envoyés ». C'est acquis et il ne faut pas
le défaire.

**Mais l'archivage est resté sur la session du praticien** — décision de
task-216, qui avait mesuré qu'une voie d'écriture dédiée rendait l'envoi *plus
lent*. C'est là qu'il gêne : il ne bloque plus l'envoi, il bloque **les lectures
suivantes du même médecin**.

### ⚠️ Établir avant de corriger — et il y a un piège précis ici

**Le remède évident est celui que task-216 a déjà mesuré et rejeté.** Rouvrir une
seconde session IMAP pour l'archivage ferait exactement ce que task-213 avait
fait et que task-215 a réfuté par contre-épreuve : *ce que la voie retirait au
verrou, elle le repayait en ouverture de connexion*, et l'envoi était **plus
lent avec elle que sans** (p95 7 874 ms sans, 10 439 et 12 573 avec).

**Ne pas refaire task-213.** Si l'US y revient, elle doit dire ce qui a changé
depuis — et le mesurer, pas le supposer.

Pistes à instruire, aucune établie :

1. **Réduire la détention, pas la déplacer.** `AppendToSent` tient le verrou
   pendant l'APPEND IMAP complet. Que fait-il exactement sous le verrou ? La
   décomposition existe-t-elle (task-252 l'a faite pour les PJ) ?
2. **Différer l'archivage hors des fenêtres d'activité du médecin.** Il est déjà
   sur le bus (task-272) : le consommateur pourrait renoncer quand le verrou est
   tenu, comme l'avait fait le consommateur de task-278 — mécanisme éprouvé, et
   son échec ne coûterait qu'un archivage retardé, jamais une erreur.
3. **Regrouper les archivages** d'un même praticien plutôt qu'une acquisition par
   envoi (2,26 acquisitions/s mesurées).

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec)
- [ ] **La cause de la détention d'`AppendToSent` est établie et écrite** dans le
      task file, chiffres à l'appui — décomposition de ce qui se fait sous le
      verrou, comme task-252 l'a fait pour le téléchargement de PJ
- [ ] Le task file dit explicitement **ce qui a changé depuis task-215/216** si
      l'US propose une seconde session — sinon, elle ne la propose pas
- [ ] Si remède : l'acquittement de l'envoi n'attend **toujours pas** l'archivage
      (acquis de task-272, non-régression testée)
- [ ] Si remède : un échec d'archivage reste **visible et tracé** (acquis de
      task-272, non-régression testée)
- [ ] Si la mesure ne désigne aucun remède sans contrepartie, **l'US s'arrête sur
      le constat** — c'est un résultat (précédents task-276 et task-279)
- [ ] Aucune donnée de santé dans les journaux ni les étiquettes

## Manual Test Plan

**Ce que l'humain valide au HAG** : qu'envoyer un message fonctionne à
l'identique, et que la copie arrive bien dans « Envoyés ».

1. Banc : `dotnet run --project src/AppHost --launch-profile https-load-test`
2. Seed 2 utilisateurs :
   `dotnet run --project tests/mss.mail.loadtest.seed -- --users 2 --messages 20 --api http://127.0.0.1:5052`
3. Envoyer un message de `loadtest-1` vers `loadtest-2` via
   `POST /api/v1/mail/sendmail` (en-têtes d'identité virtuelle habituels).
4. **Vérifier** : l'acquittement revient **sans attendre** l'archivage, et la
   copie apparaît dans « Envoyés » dans les secondes qui suivent.
5. **Vérifier** : immédiatement après l'envoi, ouvrir `INBOX` — la lecture ne doit
   pas être retardée par l'archivage en cours.
6. Provoquer un échec d'archivage (toxic `reset_peer` sur `dovecot-imap` juste
   après l'envoi) : l'échec doit rester **tracé et visible**, pas silencieux.
7. **Clôture de l'US — au banc, tir suivant**, iso-conditions du
   `report-journey-500-lot277279-20260830-180647.md` sur la **même base
   hydratée**. Critères :
   - attente p95 de `ReadFolder` **derrière `AppendToSent`** < **1 s**
     (contre 3,938 s) — lisible directement dans la table `holder`
   - attente **moyenne** de `ReadFolder` < **50 ms** (contre 82,8 ms au 29/08)
   - `send` toujours vert au SLO et **pas plus lent** qu'au tir de référence
     (p50 417 ms, p95 860) — c'est la garde anti-task-213
   - 11/11 étapes vertes

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — performance interne
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — IMAP interne au périmètre MSSanté existant
- **Tracé PGSSI-S** : **inchangé, et c'est une exigence de l'US** — l'échec
  d'archivage d'un envoi doit rester journalisé et corrélé par `traceId` (acquis
  de task-272). Un archivage rendu « discret » pour gagner du verrou serait une
  régression de traçabilité sur un geste métier.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé
