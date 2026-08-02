# todo-task-185.md — Archives IHE_XDM écrites en clair dans le répertoire temporaire et jamais supprimées

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes confidentialité
> et concurrence — remonté indépendamment par deux agents). Vérifié par le PO.

## Objective

Ne plus laisser de données de santé en clair sur le disque. Chaque message MSSanté
porteur d'une archive `ihe_xdm.zip` — la forme normale des résultats de biologie
et des comptes-rendus — écrit l'archive dans le répertoire temporaire du système
et **ne la supprime jamais**. Les fichiers s'accumulent sans borne, survivent à la
suppression du message, à la mise à la Corbeille et à toute opposition patient, et
échappent à toute politique de conservation.

Double conséquence : DSCP en clair hors du magasin géré, et saturation du disque
qui finit par casser l'enrichissement en silence.

**US backend-only (justification)** : traitement de fichiers côté serveur.

### Preuve (état actuel du code)

- `src/Application/Services/Implementation/IheXdmProcessingService.cs:47-52` :
  ```csharp
  var tempZipPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid() + ".zip");
  await using var fileStream = File.Create(tempZipPath);
  await zipPart.Content.DecodeToAsync(fileStream, cancellationToken);
  fileStream.Close();
  extractedZipPaths.Add(tempZipPath);
  ```
  La liste de chemins est renvoyée, consommée en lecture, puis **abandonnée**.
- `src/Application/Services/Implementation/BackgroundImapService.cs:503-506` —
  le même code est **dupliqué** sur le chemin d'arrière-plan.
- Vérifié : le **seul** `File.Delete` de tout `src/` est
  `src/Application/Services/Implementation/MssanteHeaderService.cs:171` — sur le
  chemin **sortant**, dans un `finally`. Le patron était donc connu ; il n'a pas
  été appliqué aux deux chemins entrants.
- Aucune tâche de balayage du répertoire temporaire nulle part.

Aggravant : l'échec d'écriture est avalé dans un `catch` qui se contente de
journaliser — une fois le disque plein, l'enrichissement produit des messages
**sans document médical** sans que rien ne remonte comme erreur.

### Contenu attendu

1. **Cycle de vie borné** : toute archive extraite est supprimée dès que son
   traitement est terminé, y compris en cas d'exception ou d'annulation
   (`try/finally`, ou un porteur jetable propre). Les deux chemins (premier plan et
   arrière-plan) doivent être couverts — de préférence en supprimant la
   duplication.
2. **Emplacement maîtrisé** : écrire dans un répertoire dédié à l'application
   plutôt que dans le temporaire partagé du système (lisible par tout utilisateur
   local sur un hôte partagé), avec des permissions restreintes.
3. **Éviter le disque quand c'est possible** : privilégier un traitement en mémoire
   ou en flux si le parseur le permet ; le passage par fichier ne doit subsister
   que s'il est réellement imposé.
4. **Balayage de sécurité au démarrage** : purger les résidus d'exécutions
   précédentes (y compris ceux déjà accumulés par le défaut actuel).
5. **Échec d'écriture visible** : un échec d'extraction ne doit pas se traduire par
   un message silencieusement dépourvu de documents médicaux — il doit être
   journalisé en erreur et détectable en exploitation.

### Hors scope

- Le nettoyage manuel des fichiers déjà accumulés en production (opération
  d'exploitation à mener par le humain ; le balayage au démarrage la couvre au
  prochain redémarrage).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : après traitement nominal d'une archive, **aucun** fichier
      résiduel (ce test doit échouer sur le code actuel — le vérifier)
- [ ] Test unitaire : exception pendant le parsing ⇒ le fichier est **quand même**
      supprimé
- [ ] Test unitaire : annulation (`CancellationToken`) ⇒ fichier supprimé
- [ ] Test unitaire : les deux chemins (premier plan et arrière-plan) sont couverts
      — idéalement par une implémentation unique partagée
- [ ] Test unitaire : le balayage au démarrage supprime les résidus d'une
      exécution précédente
- [ ] Test unitaire : un échec d'écriture est journalisé en **erreur** et ne se
      traduit pas par un message silencieusement vide de documents
- [ ] Les fichiers temporaires sont écrits dans un répertoire dédié à permissions
      restreintes, pas dans le temporaire partagé du système
- [ ] Aucune donnée de santé en clair dans les logs (jamais de chemin ni de contenu
      permettant de retrouver un patient)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Noter le contenu du répertoire temporaire applicatif avant test.
3. Envoyer vers la boîte de test 3 messages porteurs d'une archive `ihe_xdm.zip`
   (données anonymisées). Synchroniser et laisser l'enrichissement se terminer.
4. **Attendu** : les documents médicaux sont bien créés **et** le répertoire
   temporaire est revenu à son état initial — zéro archive résiduelle. Avant
   correctif, trois archives y demeurent indéfiniment.
5. **Cas d'échec** : envoyer un message avec une archive volontairement corrompue →
   erreur journalisée explicitement, et **aucun** fichier résiduel.
6. **Balayage au démarrage** : déposer manuellement un faux résidu dans le
   répertoire, redémarrer l'application → le résidu a disparu.
7. Vérifier les permissions du répertoire dédié (non lisible par un autre
   utilisateur local).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté, documents de santé
- **Exigences DSR honorées** : correctif de conformité PGSSI-S — confidentialité
  des données au repos et durée de conservation
- **INS** : les archives contiennent des documents CDA porteurs d'INS et de traits
  d'identité — d'où la qualification DSCP au repos
- **Authentification PS** : inchangée
- **Habilitations** : sur un hôte partagé, le temporaire système est lisible par
  défaut par d'autres utilisateurs locaux — population non habilitée aux DSCP
- **Interop CI-SIS** : archives IHE_XDM et documents CDA r2 ; parsing inchangé
- **Tracé PGSSI-S** : journaliser les échecs d'extraction et le résultat du
  balayage au démarrage (évènements techniques, sans contenu)
- **Consentement patient** : non applicable — mais noter que ces fichiers
  **survivent** à une opposition patient et à la suppression du message, ce qui
  contredit l'effectivité des droits
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — les données doivent rester dans le magasin géré du
  périmètre HDS, pas dans un temporaire non maîtrisé
- **AIPD / impact RGPD** : **à mettre à jour** — manquement à la limitation de
  conservation (art. 5.1.e) et à la sécurité (art. 32). Qualifier avec le humain le
  volume accumulé en production et organiser la purge.

## Branches
- `api-mail` (pushed) : fix/task-185-ihe-xdm-temp-lifecycle — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-185-ihe-xdm-temp-lifecycle
- `dtos-mss` (pushed, auto-inclus) : fix/task-185-ihe-xdm-temp-lifecycle — aucun contrat attendu (US backend-only)

## Develop log

### Le test principal constaté RED avant correctif (DOD 3)

Une sonde jetable (`IheXdmScratchProbeTests`) a été écrite contre le code
d'origine, puis remplacée par la suite définitive :

```
Échoué!  - échec : 1, réussite : 0
  archive résiduelle après traitement : {guid}.zip
```

### Correction de l'énoncé — le nœud n'est pas un `File.Delete` oublié

C'est la **propriété** qui manquait. Les chemins ne sont pas consommés sur place :
ils voyagent dans `FetchedMail` / `FetchedBackgroundMail` jusqu'à la persistance.
Un `try/finally` au site d'extraction — la forme évidente, et celle que suggère
l'énoncé — **aurait supprimé les archives avant leur lecture**. D'où un lot
jetable qui traverse la même frontière que les chemins.

Cela explique aussi pourquoi le patron était « connu mais inappliqué » : le seul
`File.Delete` de `src/` est sur le chemin sortant, où le fichier est consommé
dans la même méthode. Le patron n'était pas transposable tel quel.

### Point 3 du contenu attendu — écarté, avec sa raison

« Éviter le disque quand c'est possible » : `XDM.Load(fileName, xsdPath)` fait un
`ZipFile.OpenRead(fileName)`. Le parseur **n'accepte qu'un chemin**, et il vit
dans `interop-cda` — repo porteur de contrat, non listé dans les `Repos` de cette
task. Le fichier est donc **réellement imposé**, par une API hors périmètre.
Candidat pour une task dédiée.

## Sonar log

Deux findings **introduits par la task**, tous deux corrigés :

| Règle | Emplacement | Correctif |
|---|---|---|
| `csharpsquid:S3874` | `IheXdmScratch.cs` — `CreateFile(out string)` | tuple de retour |
| `csharpsquid:S2699` | `IheXdmScratchTests.DisposeIsIdempotent` | le test vérifie désormais la suppression effective, pas seulement l'absence d'exception |

Après correction : **0 issue sur les 7 fichiers touchés**.

> ⚠️ KPIs projet inexploitables depuis task-212 (`agents/sonar.md` périmé).

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/141 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche sans commit (US backend-only)

## Code Review Summary

**APPROVED** — 17 fichiers, 0 blocage.

- `IheXdmScratch.cs` — ✅ répertoire dédié 0700 / fichiers 0600, lot jetable
  propriétaire, chemin suivi **dès l'ouverture** (un fichier partiellement écrit
  est supprimé lui aussi), `Dispose` idempotent et non levant.
- `IheXdmScratchSweepService` — ✅ best-effort au démarrage ; une purge qui
  empêcherait le démarrage transformerait un correctif de confidentialité en
  panne de disponibilité.
- `IheXdmProcessingService` — ✅ l'échec est compté au lieu d'être avalé.
- `BackgroundImapService` — ✅ duplicata supprimé (1 481 caractères), passe par
  le service partagé.
- `ImapService` / transporteurs — ✅ `IDisposable` sur les deux records, `using`
  là où la consommation est locale.

### Observations non bloquantes
- Deux flakies pré-existants (`MailExportServiceTests` PdfPig ;
  `FlagsmithFeatureFlagServiceTests` `MeterListener`) sont apparus une fois
  chacun sur les exécutions de la suite complète, verts en isolation et sans
  lien avec ce diff. Dernière suite complète propre : **3 288 verts**.

## Merged
- `api-mail` : **5393eb6** — squash de la PR #141, mergée le 2026-08-01
- `dtos-mss` : aucune PR (branche sans commit) ; ref distant supprimé

Refs distants supprimés sur les deux repos ; **branches locales conservées**.

> **Reste dû, hors DOD et hors forge** : qualifier avec le DPO le **volume de
> fichiers déjà accumulés en production** et mettre à jour l'AIPD (limitation de
> conservation art. 5.1.e, sécurité art. 32). Le balayage au démarrage purge ces
> résidus au prochain redémarrage, mais la qualification reste un acte humain.
>
> **Candidat de suivi** : surcharge `Stream` sur `XDM.Load` dans `interop-cda`,
> qui permettrait de supprimer complètement le passage par fichier.
