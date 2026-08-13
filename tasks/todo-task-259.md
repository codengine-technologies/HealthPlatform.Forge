# todo-task-259.md — `RemoveRange` sur une collection de navigation la modifie pendant qu'il l'énumère : l'enrichissement de contact échoue sous concurrence

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. **task-250** a travaillé le même bloc (traduction du
conflit de concurrence en `ConflictException` et rejeu) ; ce défaut-ci est
**distinct** : il se produit **avant** `SaveChangesAsync`, donc avant la
frontière que task-250 a posée, et le rejeu ne le rattrape pas.
**Priorité**: **3** — sans effet sur le débit ni sur la lecture du médecin, mais
c'est une **perte silencieuse d'enrichissement de contact** : l'exception est
journalisée puis avalée, et l'apport du message est perdu sans que personne ne le
sache.

## Objective

Que l'enrichissement d'un contact praticien aboutisse quand deux messages
concernant le **même** praticien sont traités simultanément.

## Ce qui est établi

**Mesuré** — campagne task-255 du 2026-08-13, banc local, quatre occurrences par
série de trois tirs, reproduites sur **les deux** séries (hôte affamé et hôte
calme), sur des praticiens différents (`loadtest-1`, `-3`, `-5`, `-7`) :

```
[PractitionerContactService] ❌ Error creating/updating contact for DR Pierre DIDOT
System.InvalidOperationException: Collection was modified; enumeration operation may not execute.
   at Microsoft.EntityFrameworkCore.Internal.InternalDbSet`1.RemoveRange(IEnumerable`1 entities)
   at ContactRepository.UpdateAsync(ContactDto contact)          ContactRepository.cs:206
   at PractitionerContactService.UpdateWithConflictRetryAsync(…)  PractitionerContactService.cs:201
   at PractitionerContactService.EnrichContactAsync(…)            PractitionerContactService.cs:87
   at PractitionerContactService.CreateOrUpdateContactAsync(…)    PractitionerContactService.cs:52
```

Le corpus du banc adresse le **même praticien** depuis plusieurs messages, ce qui
explique que le défaut sorte à tous les coups sur une campagne d'enrichissement.

**Lu dans le code, et non mesuré** — c'est une lecture structurelle, à confirmer
par un test avant tout correctif : `ContactRepository.UpdateAsync` appelle

```csharp
db.ContactMssAddresses.RemoveRange(entity.MssAddresses);
db.ContactTags.RemoveRange(entity.Tags);
db.ContactGroupMembers.RemoveRange(entity.GroupMembers);
```

`entity.MssAddresses` est une **collection de navigation suivie par EF**.
`RemoveRange` marque chaque entité comme supprimée, ce qui déclenche le
raccordement des navigations — donc **modifie la collection qu'il est en train
d'énumérer**. L'énumérateur se plaint, exactement comme le ferait un
`foreach` qui supprime dans la liste qu'il parcourt.

**Ce que ça coûte** : l'exception remonte jusqu'à `CreateOrUpdateContactAsync`
qui la journalise en `Error` et **s'arrête là**. Le message a bien été enrichi,
mais le **contact** ne l'a pas été. Aucune alerte, aucun rejeu — le rejeu de
task-250 se déclenche sur `ConflictException`, un type qui n'est levé
**qu'après** `SaveChangesAsync`, donc jamais atteint ici.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est le même défaut que task-250.** Celui-là était un
  conflit de concurrence **à l'écriture** ; celui-ci est une erreur d'énumération
  **avant** l'écriture. Les commentaires en place décrivent le premier — ne pas
  les confondre, ni les supprimer.
- **Ne pas remplacer le rejeu par une suppression ensembliste.** Le commentaire
  de task-250 explique pourquoi, et c'est un constat empirique :
  `ExecuteDeleteAsync` est **relationnel uniquement** et lève sur le provider
  InMemory dont dépendent les tests de ce dépôt. Un correctif qui rend le code
  testable seulement sur le provider le plus riche est refusé (leçon task-247).
- **Ne pas présumer que matérialiser la collection suffit** sans le prouver.
  C'est le correctif le plus probable, il tient en un appel — raison de plus pour
  exiger un **test qui échoue d'abord**.
- **Ne pas élargir aux contacts patient** sans mesure : `CreatePatientContact`
  suit un chemin voisin, mais aucune occurrence n'a été relevée. Vérifier, et
  dire ce qu'on trouve.

## Definition of Done

- [ ] Build passe (0 erreur), tests passent (0 échec)
- [ ] Un **test unitaire reproduit le défaut d'abord** (rouge sans le correctif,
      vert avec) : mise à jour d'un contact portant plusieurs adresses MSS,
      étiquettes et appartenances de groupe
- [ ] Le même contrôle couvre les **trois** collections (`MssAddresses`, `Tags`,
      `GroupMembers`) — corriger la première et oublier les deux autres laisserait
      le défaut en place
- [ ] Un test couvre le cas **concurrent** : deux enrichissements du même contact
      ; **les deux apports survivent** (c'est la promesse de task-250, qui ne doit
      pas être défaite)
- [ ] Le chemin **contact patient** est vérifié et le verdict écrit : même défaut
      corrigé, ou absence de défaut justifiée
- [ ] Les tests passent sur le provider **InMemory** utilisé par ce dépôt
- [ ] Le rejeu et la traduction `DbUpdateConcurrencyException` →
      `ConflictException` de task-250 sont **inchangés**
- [ ] Une campagne d'enrichissement au banc ne produit **plus aucune**
      `InvalidOperationException` depuis `ContactRepository`

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`), seeder 8 praticiens × 20 messages
- Purger, préchauffer, puis lancer `tests/loadtest-k6/run.sh enrich --env VUS=8`
- **Ce qu'il faut voir dans Seq**, filtre
  `@Level = 'Error' and SourceContext like '%PractitionerContactService%'` :
  **zéro** événement, là où la campagne task-255 en produisait quatre par série
- Ouvrir la fiche d'un praticien destinataire de plusieurs messages depuis
  l'application : ses adresses MSS, étiquettes et groupes doivent être **complets
  et sans doublon**
- Contre-épreuve du test : revenir au code d'origine et vérifier que le test
  unitaire **échoue**

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — correction de défaut
- **Exigences DSR honorées** : aucune exigence nouvelle
- **INS** : ⚠️ un contact praticien porte des **données à caractère personnel**
  (nom, RPPS, adresses MSSanté). Aucun journal ni message d'exception ajouté par
  cette US ne doit en publier — le journal existant nomme déjà le praticien
  (`FullName`), ce qui est **à réduire** au passage : un identifiant technique
  suffit à diagnostiquer
- **Interop CI-SIS** : sans objet — le contact n'est pas un document clinique
- **Habilitations** : le cloisonnement « une base par praticien » est inchangé
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : ⚠️ la perte silencieuse d'enrichissement est aussi un
  défaut de traçabilité — après correctif, un échec d'enrichissement de contact
  doit rester **visible** et non avalé
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : ⚠️ retirer le nom du praticien du journal d'erreur est
  une réduction de la donnée journalisée — à faire, pas à documenter seulement
