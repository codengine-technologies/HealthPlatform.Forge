# todo-task-271.md — Une détention de session à 60 s est un timeout qui a un nom, pas un p95 qu'on subit

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

La campagne du 2026-08-23 montre une anomalie **invisible du médecin mais au
plafond de l'instrument** : la détention du verrou `imap_session` par
`GetFolders` atteint **60,000 s au p95** (une valeur au plafond exact désigne
un timeout, pas un travail de 60 s), et la route serveur `GET /mail/folders`
publie un p95 OpenTelemetry de **56,8 s** — alors que la même étape vue du
client k6 vaut 155 ms au p95. L'écart dit que ces occurrences vivent hors du
parcours jugé : vraisemblablement dans la **chauffe** (établissement de ~300
sessions fraîches au front de chaque palier) et l'extinction (4 034
`TaskCanceledException` sur le tir, ~1 par rotation de session — nominal).

**Le problème n'est pas (encore) une lenteur, c'est un angle mort.** Tant que
ces détentions à 60 s ne portent ni cause ni étiquette, elles polluent trois
lectures : le p95 serveur de la route (inutilisable pour un SLO interne), la
table des verrous (un p95 au plafond écrase tout), et toute campagne future
qui voudrait juger `GetFolders`. Le précédent est connu : « une étiquette
absente n'établit pas qu'une opération n'a pas eu lieu » (task-214) — ici,
une valeur au plafond n'établit pas ce qui l'a produite.

**Contenu attendu — caractériser, puis étiqueter ; corriger seulement si la
cause le réclame** :

1. **Établir sur pièce** ce qui détient `imap_session` 60 s sous `GetFolders` :
   quel timeout expire (connexion IMAP ? TLS ? le budget du verrou lui-même ?),
   sur quel chemin (première connexion d'une session fraîche ? reconnexion
   après péremption ?), à quels moments du tir (fronts de palier ? extinction ?).
   Les traces Seq du tir 2026-08-23 (`TraceId` des requêtes `folders` >10 s)
   et le code du gestionnaire de sessions suffisent — pas besoin d'un nouveau
   tir pour instruire.
2. **Rendre la lecture honnête** : si la cause est l'établissement de session
   (chauffe), la détention d'établissement doit être **distinguable** de la
   détention d'exploitation (étiquette dédiée sur l'histogramme du verrou, ou
   exclusion motivée), pour que le p95 de `GetFolders` redevienne lisible.
3. **Si un vrai défaut apparaît** (timeout mal dimensionné, verrou tenu
   pendant une connexion réseau qui n'en a pas besoin — le verrou n'a pas à
   couvrir TCP+TLS si la session n'est pas encore partagée) : le corriger fait
   partie de la US, avec la preuve rouge d'abord.

**Gain attendu** : un p95 `GetFolders` opposable ; au mieux, un établissement
de session qui ne tient plus le verrou pendant le handshake (moins de
contention aux fronts de palier — là où la chauffe consomme déjà 56-60 % des
fenêtres).

## Definition of Done

- [ ] Build passes (0 errors), tests pass (0 failures) sur api-mail
- [ ] La cause des détentions à 60 s est **écrite dans la task** avec les
      `TraceId` à l'appui (traces du tir 2026-08-23) et le timeout nommé
      (valeur + endroit du code)
- [ ] La détention d'établissement de session est distinguable de la détention
      d'exploitation dans la télémétrie du verrou (nouvelle étiquette testée),
      OU son exclusion est motivée par écrit si l'analyse montre qu'elle n'a
      pas sa place dans cet histogramme
- [ ] Si un correctif est livré : preuve rouge d'abord (test qui capture le
      comportement fautif avant le fix), puis vert
- [ ] Si aucun correctif n'est justifié : la task le **dit** avec la mesure à
      l'appui — « caractérisé, bénin, étiqueté » est un livrable recevable
- [ ] `report.py` : la table des verrous reste correcte avec la nouvelle
      étiquette (selftest du harnais vert, zéro SKIP)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Rejouer l'analyse sur les traces existantes : Seq, fenêtre
  2026-08-23T17:32→20:07 UTC, filtre
  `RequestPath like '%/mail/folders' and ElapsedMs > 10000` → dérouler 2-3
  `TraceId` et confronter aux détentions du verrou
- Banc local, tir court avec rotation de session forcée
  (`SESSION_ROTATION` élevé) : vérifier que les détentions d'établissement
  portent la nouvelle étiquette et que le p95 d'exploitation de `GetFolders`
  reste < 1 s
- Vérifier `tests/loadtest-k6/selftest.sh` : 0 échec, 0 SKIP

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — observabilité/caractérisation interne
- **Exigences DSR honorées** : non applicable — aucun changement fonctionnel
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — les histogrammes de verrou ne portent aucune donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé
