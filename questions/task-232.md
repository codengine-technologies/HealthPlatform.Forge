# questions/task-232.md — Phase 1 livrée, Phase 2 en attente de la seule mesure qui tranche

**Ouvert le** 2026-08-05 · **Task** : task-232 · **État** : ⛔ **CLOS le 2026-08-05 — la US a
été ANNULÉE par décision humaine.**

> La décision demandée en fin de document a été tranchée : ni tir au banc, ni PR. La task est
> archivée (`tasks/archived/archived-task-232.md`). Ce fichier est conservé pour ses **mesures**
> et pour la **piste `htmlBodySanitizer`**, qui reste ouverte et ne dépend pas de l'hypothèse
> abandonnée. Le témoin `served_from` décrit ici n'est **pas** sur `develop` — il dort dans le
> commit `3fd1dac`.

## Pourquoi ce fichier existe

La US ordonne explicitement l'arrêt :

> *si la cause n'est **pas** l'UidValidity (part `served_from=imap` faible ou désalignement
> nul), **s'arrêter et ouvrir `questions/task-232.md`** avec les mesures — ne pas corriger
> à l'aveugle.*

La seule mesure de désalignement que je peux produire localement est **nulle**. Je m'arrête
donc là où la US le demande, et je livre ce qui rendra le verdict possible.

## Ce qui est livré (Phase 1)

Le témoin `served_from` — **le livrable qui rend la mesure discriminante**.

| Élément | Détail |
|---|---|
| Compteur | `mssante_mail_content_served_total`, étiquette `served_from` ∈ {`db`, `imap`} |
| Point d'appel « base » | juste avant le retour immédiat de `GetEmailContentInternalAsync` |
| Point d'appel « imap » | **avant** la prise du verrou de session et tout aller-retour |
| Tests | 7 (5 sur l'enregistreur, 2 sur le point de décision) |
| Preuve ROUGE | témoin inversé sur le chemin base → le test du chemin base échoue, l'autre passe |

### ⚠️ Un écart assumé avec la consigne littérale de la US

La US demandait d'*« ajouter au compteur de sollicitations (task-225) une dimension
`served_from` »*. **Cela n'aurait pas produit une mesure discriminante**, et c'est
arithmétique : servir depuis la base signifie **zéro sollicitation**. Une dimension posée sur
ce compteur ne se serait donc **jamais** incrémentée avec la valeur `db` — on aurait obtenu un
numérateur IMAP sans dénominateur, incapable de dire quelle **part** des ouvertures part vers
le serveur, c'est-à-dire précisément la grandeur à prouver.

Le témoin compte donc des **lectures**, pas des allers-retours. C'est un compteur distinct,
et le raisonnement est écrit dans le code (`MailContentSource`, `MailProcessingMetrics`).

### Pourquoi le témoin compte l'intention et non le succès

Sur le chemin IMAP il est posé **avant** la connexion : une ouverture qui part vers le serveur
puis échoue est comptée `imap`. Délibéré — la grandeur cherchée est « à quelle fréquence
emprunte-t-on le chemin froid », pas « combien de fois y réussit-on ». Un compteur posé sur le
succès **sous-estimerait** la part IMAP, donc minorerait le défaut.

## La mesure que j'ai pu faire, et ce qu'elle vaut

Base de **développement** (un praticien), relevée le 2026-08-05 :

```sql
SELECT m."FolderPath", count(*), count(DISTINCT m."UidValidity") FROM "Mails" m GROUP BY 1;
-- INBOX | 51 | 1   (génération unique : 1735566573)

SELECT f."Path", f."UidValidity", ... FROM "MailFolders" f LEFT JOIN "Mails" m ON ...
-- INBOX : 51 mails, 51 alignés, 0 désalignés, 0 à génération zéro
-- tous les autres dossiers : aucun mail
```

**Désalignement : nul.** 51 messages sur 51 portent exactement la génération de leur dossier.
Aucune ligne à `UidValidity = 0`, donc **la fenêtre de dérive décrite par la US ne s'est pas
produite ici** — l'estampillage (`SyncUidValidityAsync`, branche `Adopted`) exige
`UidValidity == 0` au moment précis de l'adoption.

### ⚠️ Ce que cette mesure ne permet PAS de conclure

Elle **n'infirme pas** l'hypothèse, et il serait malhonnête de le prétendre :

- ce n'est **pas la base du banc** — la US demande explicitement la mesure sur le banc ;
- l'échantillon est faible : **un seul dossier peuplé**, 51 messages, **une seule
  génération**. Un désalignement suppose au moins deux générations en présence ;
- cette base a été **resynchronisée récemment** (`LastSyncedAt` 2026-08-05T14:54). Le même
  passage a d'ailleurs corrigé un `FolderType` que j'avais relevé faux plus tôt (cf. la
  correction apportée aux documents de task-233) : **l'état de cette base bouge**, et un
  relevé y est un instantané, pas une propriété.

Autrement dit : la seule mesure disponible **ne soutient pas** l'hypothèse, et la mesure que
la US spécifie **n'est pas productible** sans le banc.

## Ce qui bloque, et ce qu'il faut pour débloquer

**Le banc n'est pas monté.** Il faut, conformément au Manual Test Plan de la US :

1. monter le banc (skill `loadtest-skill`) ;
2. **un tir court suffit** (`n10`) — relever
   `mssante_mail_content_served_total` ventilé par `served_from` sur la route contenu ;
3. exécuter sur **la base du banc** les trois requêtes de désalignement du Manual Test Plan.

### Le verdict à rendre ensuite, et il n'a que deux branches

| Mesure au banc | Conduite |
|---|---|
| part `served_from=imap` **forte** ET désalignement **non nul** | Phase 2 : aligner les tests « déjà enrichi » sur le filtre de génération de la lecture, estampiller à l'adoption |
| part `imap` **faible** OU désalignement **nul** | **la cause est ailleurs** — ne pas corriger l'UidValidity, ouvrir l'investigation sur une autre hypothèse avec les chiffres |

Le témoin livré ici rend ce verdict possible dans les deux cas ; il ne le préjuge pas.

## Une piste à ne pas perdre si la mesure infirme l'UidValidity

La US note que trois opérations k6 s'agrègent sous la même étiquette (`read_content`,
`read_content_cold`, `patient_docs`). Si la part `served_from=db` s'avère **proche de 100 %**
alors que l'étape 3 reste à 407 ms, alors le coût n'est **pas** dans le choix de la source, et
les suspects deviennent la **sérialisation du contenu** (`BodyHtml` volumineux, assainissement
AngleSharp à chaque lecture — `htmlBodySanitizer.Sanitize` tourne **sur le chemin chaud**, à
chaque ouverture, sur tout le corps HTML) ou le harnais lui-même. L'assainissement défensif de
task-088 est un candidat sérieux que la US ne mentionne pas, et le témoin livré permettra de
l'isoler : `served_from=db` à 100 % avec un p50 élevé le désignerait presque à coup sûr.

## Décision demandée à l'humain

1. Monter le banc et produire le tir court, **ou** dire que la mesure attendra.
2. Si elle attend : la PR de Phase 1 est-elle ouverte telle quelle ? La US le prévoit — la
   contre-épreuve y est déclarée *« bloquante pour le merge, pas pour la PR »* — et le témoin
   n'a de valeur que déployé.
