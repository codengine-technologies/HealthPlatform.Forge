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
