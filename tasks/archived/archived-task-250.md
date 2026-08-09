# todo-task-250.md — Deux médecins qui correspondent avec le même confrère perdent une écriture

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune
**Priorité**: **2** — rare aujourd'hui (1 occurrence sur 133 214 requêtes), mais
c'est une **écriture perdue**, pas une lenteur : elle est silencieuse et sa
probabilité **croît avec la population**.

## Objective

Qu'une mise à jour concurrente d'un contact praticien ne se perde plus.

## Ce qui est établi

Tir local 200 du 2026-08-08, palier 200, une occurrence :

```
DbUpdateConcurrencyException : The database operation was expected to affect
1 row(s), but actually affected 0 row(s)
  ContactRepository.UpdateAsync (ContactRepository.cs:180)
  ← PractitionerContactService.EnrichContactAsync (PractitionerContactService.cs:108)
  ← PractitionerContactService.CreateOrUpdateContactAsync (:51)
```

Deux passages concurrents enrichissent le **même** contact praticien ; le second
ne trouve plus la ligne dans l'état qu'il avait lu, n'affecte aucune ligne, et
lève. L'exception est journalisée puis **avalée** : côté produit, l'enrichissement
du contact est simplement **perdu**, sans que personne ne le sache.

**Pourquoi la fréquence va monter** : le cas se produit quand deux praticiens
correspondent avec le **même** confrère au même moment. À 200 médecins c'est rare ;
la probabilité croît avec le carré de la population, pas linéairement.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est bénin parce que c'est rare.** Une donnée d'annuaire
  qui ne se met pas à jour se voit des semaines plus tard, ou jamais.
- **Ne pas présumer que la ligne a été supprimée.** `0 row(s) affected` en
  concurrence optimiste signifie « l'état a changé depuis la lecture » — le plus
  probable est une **écriture concurrente**, pas une suppression. À établir avant
  de choisir entre un `UPSERT` et une relecture sur conflit.

## Definition of Done

- [ ] Une mise à jour concurrente du même contact n'échoue plus silencieusement :
      soit elle est fusionnée (`UPSERT`), soit elle est rejouée sur conflit
- [ ] La stratégie retenue est **justifiée par la cause établie**, pas choisie par
      défaut : quel état a changé, et pourquoi
- [ ] **Test de concurrence** : deux mises à jour simultanées du même contact ;
      l'état final contient les deux enrichissements, ou la règle de préséance est
      explicite et testée
- [ ] Si un cas reste irréconciliable, il est **journalisé comme un conflit
      métier** — jamais avalé
- [ ] Zéro `DbUpdateConcurrencyException` sur un tir 200

## Manual Test Plan

- Depuis deux praticiens du banc, recevoir chacun un message du **même** confrère
  au même moment (deux envois simultanés)
- Vérifier dans les deux boîtes que la fiche du confrère est complète et cohérente
  (nom, spécialité, adresse MSSanté)
- Vérifier dans Seq l'absence de `DbUpdateConcurrencyException`

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — correction de robustesse
- **Exigences DSR honorées** : aucune exigence nouvelle ; la US **restaure** la
  fiabilité d'une donnée d'annuaire professionnel
- **INS** : non applicable — il s'agit de contacts **praticiens**, pas de patients
- **Habilitations** : le contact porte un **RPPS** ; une fusion ne doit jamais
  mélanger deux praticiens distincts — c'est le risque fonctionnel n°1 de cette US,
  et il doit être couvert par un test
- **MSSanté** : l'adresse du contact peut être personnelle ou organisationnelle —
  la fusion doit préserver le type
- **Authentification PS / Consentement / Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : un conflit non résolu doit être traçable
- **Hébergement HDS** : sans objet
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-250-contact-concurrent-update
- `dtos-mss` (pushed, auto-inclus) : feat/task-250-contact-concurrent-update

> ⚠️ Démarrée alors que `wip-task-254` est en test au banc sur une autre machine.
> Recouvrement de fichiers **mesuré nul** : 254 touche `ImapService.cs` /
> `MailServerSolicitationRecorder.cs` / `report.py`, 250 touche `ContactRepository.cs` /
> `PractitionerContactService.cs`. Dérogation assumée à la règle « un seul wip ».

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/180 — label `awaiting-human-merge`
- **dtos-mss** : aucun commit → **pas de PR** (branche vide)

## Code Review Summary

**APPROVED** — 4 fichiers, 0 blocage.

| Fichier | Verdict |
|---|---|
| `ContactRepository.cs` | ✅ traduction à la frontière, cause conservée en `InnerException` ; `RemoveRange` **conservé délibérément**, le commentaire dit pourquoi (portabilité du provider) |
| `PractitionerContactService.cs` | ✅ rejeu **borné à 1**, relecture + ré-application, conflit métier en `Error` ; `ApplyEnrichment` pure |
| `ContactConcurrentUpdateTests.cs` | ✅ 3 cas sur **vrai Postgres** (l'InMemory ne vérifie pas les lignes affectées) |
| `PractitionerContactServiceTests.cs` | ✅ 3 cas du rejeu, dont le témoin « déjà à jour → aucun rejeu inutile » |

**Frontière de couche vérifiée sur le diff** : **0 `using Microsoft.EntityFrameworkCore`**
dans la couche Application.

### Validation

Build 0 erreur. domain 136 · infrastructure 436 · api 660 · application 2 102 ·
**integration 384, 0 échec**. `develop` mergée (apporte 247 + 248) — **aucun conflit**.

Deux échecs `application` apparus **une fois**, non reproduits sur deux runs verts
consécutifs ; je ne peux pas les nommer, la sortie identifiante est revenue verte.

### DOD

| Critère | État |
|---|---|
| Plus d'échec silencieux — **rejoué sur conflit** | ✅ |
| Stratégie **justifiée par la cause établie** | ✅ |
| Test de concurrence, préséance explicite et testée | ✅ |
| Conflit irréconciliable journalisé, **jamais avalé** | ✅ |
| **Zéro `DbUpdateConcurrencyException` sur un tir 200** | ⏳ **exige un tir** |

### ⚠️ Reste ouvert

**`/sonar` n'a pas été rejoué** sur cette task, qui modifie du C#.

Commits : `b3c21ab` (fix), `f30ce27` (merge develop).

## Merged

- **api-mail** : PR #180 squash-mergée sur `develop` — commit **`bf4e745`** (2026-08-09).
- **CI `develop`** : ✅ verte, vérifiée **sur ce sha précis** (`headSha`) — `develop`
  bouge en parallèle sur cette EPIC, « le dernier run » ne prouverait rien.
- Branche distante supprimée ; **branche locale conservée**.
- **dtos-mss** : branche restée vide, aucune PR — non supprimée.
- Attestation humaine `--i-tested` fournie le 2026-08-09.

### Ce que cette task laisse comme leçon transférable

**Deux pièges de portabilité de provider dans la même session.** task-247 :
`roots.Any(r => References.Contains(r))` passe sur Npgsql, pas sur InMemory.
task-250 : `ExecuteDeleteAsync` est relationnel uniquement et lève sur InMemory. Dans
les deux cas le constat a été **empirique** — un test unitaire tombé — et non
théorique. La règle est désormais écrite dans les deux fichiers : *le code de
production ne doit pas être testable seulement sur le provider le plus riche.*

**Et deux tests verts par construction, démasqués par mutation.** task-247 : la
déduplication par `MessageId` (les fixtures utilisent des `MessageId` uniques).
task-250 : deux `UpdateAsync` séquentiels ne peuvent pas se croiser. Dans les deux cas
la preuve par mutation a été le seul moyen de le voir — un test qui passe ne dit rien
tant qu'on n'a pas vérifié qu'il sait échouer.

### ⚠️ Reste ouvert après merge

- **Dernier critère du DOD** : zéro `DbUpdateConcurrencyException` sur un tir 200 —
  exige un tir. Le mécanisme est corrigé et testé ; son **absence en conditions
  réelles** reste à constater.
- **`/sonar` n'a jamais été rejoué** sur cette task, qui modifie du C#.
