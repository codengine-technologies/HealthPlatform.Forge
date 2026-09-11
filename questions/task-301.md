# questions/task-301.md — Le répertoire de travail IHE-XDM est unique par machine et son balayage supprime tout : défaut de test **et** de production

**Task** : task-301 (EPIC E016)
**Statut** : task-301 est **livrée** (harnais partagé, 3 passes vertes). Ce document porte un **défaut découvert en la faisant**, hors de son périmètre.
**Date** : 2026-09-11
**Gravité** : à instruire — implication production plausible sur du contenu clinique

---

## Comment il a été trouvé

task-301 a activé le parallélisme des collections de test
(`parallelizeTestCollections: true`, `maxParallelThreads: 4`). Résultat mesuré :

- **durée 90 s → 27 s (×3,3)** — le gain est réel ;
- **3 échecs**, tous d'extraction CDA, tous « collection vide » :
  - `CdaParsingIntegrationTests.ParseCardiologyPrescriptionReturnsDocumentWithMetadata`
  - `CdaParsingIntegrationTests.ParseImagingReportReturnsDocumentWithMetadata`
  - `CdaDocumentExtractionNonRegressionTests(folder: "CR-BIO_2021.01_Microbiologie_V2")`

Le parallélisme a été **retiré** et les 3 tests **n'ont pas** été mis en
quarantaine : le défaut n'est pas dans les tests.

## Le mécanisme

`src/Application/Helpers/IheXdmScratch.cs` :

```csharp
// ligne 32
Root = root ?? Path.Combine(Path.GetTempPath(), DirectoryName);   // "mss-ihe-xdm"

// ligne 112 — Sweep(), appelé au démarrage
foreach (var file in Directory.EnumerateFiles(Root))
{
    File.Delete(file);      // TOUS les fichiers, sans condition
}
```

Le répertoire de travail est **unique par machine**, et le balayage de démarrage
supprime **tous** les fichiers qu'il y trouve — **sans filtre d'âge, sans
marqueur de propriétaire, sans distinction entre une archive résiduelle et une
archive en cours de traitement**.

En test : deux collections démarrent en parallèle, la seconde balaie les
archives que la première est en train d'extraire → « collection vide ».

## Pourquoi ça dépasse les tests

**api-mail tourne en 5 réplicas.** Si plusieurs réplicas partagent le même
espace temporaire (même hôte, même volume monté, ou un `emptyDir` partagé), le
démarrage ou le redémarrage de **l'un** supprime les archives IHE-XDM **en vol**
des **autres**.

Conséquence : une archive de compte rendu disparaît en cours d'extraction. Le
traitement n'échoue pas bruyamment — il rend **zéro document clinique**, ce qui
est exactement la signature observée en test. Et le repo connaît déjà le coût de
ce mode de défaillance : une perte de contenu clinique silencieuse, sans erreur
levée, est le pire cas (cf. le marqueur d'enrichissement `MailContents`).

**Ce n'est pas démontré en production** — cela dépend de la façon dont
`TMPDIR` / le volume temporaire est monté par réplica. C'est précisément ce
qu'il faut vérifier.

## Ce que ça explique aussi

L'échec CI #1 de task-300 —
`CdaDocumentExtractionNonRegressionTests(folder: "CR Imagerie")`, « collection
vide » sur Linux, vert sur Windows — est **le même symptôme, la même famille de
tests, le même répertoire partagé**. L'hypothèse d'un lien est forte : sur le
runner Linux, l'ordre d'exécution fait qu'une autre suite balaie le répertoire
pendant que celle-ci extrait.

Si cette hypothèse est confirmée, **un seul correctif ferme les deux sujets** :
l'échec CI de task-300 et le blocage du parallélisme de task-301.

## Ce que je recommande

1. **Vérifier d'abord la production** : est-ce que deux réplicas d'api-mail
   peuvent voir le même `Path.GetTempPath()` ? (montage du volume temporaire
   dans `DevOps/`, `TMPDIR` du conteneur). C'est une question de configuration,
   elle se tranche en lisant un manifeste.
2. **Isoler le répertoire par processus et par exécution** — par exemple un
   sous-répertoire dérivé de l'identifiant de processus et d'un jeton de
   démarrage —, et **borner le balayage** à ce sous-répertoire, ou à défaut aux
   fichiers dont l'âge dépasse un seuil sûr. Un balayage qui ne peut pas
   distinguer « résiduel » de « en vol » ne devrait pas supprimer.
3. **Une fois corrigé** : réactiver `parallelizeTestCollections` (le gain mesuré
   est ×3,3 sur le projet d'intégration) et retirer les deux avertissements
   posés dans `xunit.runner.json` et le `## Develop log` de task-301.

Une US dédiée me paraît justifiée — elle fermerait l'échec CI de task-300, le
blocage de parallélisme de task-301, et un risque de perte de contenu clinique
en production. La forge ne crée pas de task d'elle-même : c'est ton arbitrage.
