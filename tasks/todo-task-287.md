# todo-task-287.md — Rendre mesurable la conformité des en-têtes MSSanté à l'émission

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009

## Objective

Quatre en-têtes SMTP réglementaires sont posés sur chaque message MSSanté sortant
(`X-MSS-CODECDA`, `X-MSS-INS`, `X-MSS-NIL`, `X-MSS-MES`). Leur pose est
**best-effort par conception** : si quoi que ce soit échoue — CDA malformé,
archive illisible, valeur non configurée — le message part quand même, sans ses
en-têtes. C'est un bon choix : le courrier d'un médecin ne doit pas s'arrêter
sur une pièce jointe abîmée.

Le problème n'est pas là. Le problème est que **rien ne compte ces
dégradations**. Un message peut partir non conforme à une exigence Ⓔ que
l'opérateur MSSanté audite, et personne ne l'apprend — sauf à relire les
journaux à la main.

Ce n'est pas théorique. `X-MSS-NIL` n'a **jamais** été émis en production, parce
que le numéro de produit convergence n'était pas configuré. Le code journalisait
consciencieusement un avertissement à chaque envoi. Le défaut a été trouvé le
2026-09-01 en **lisant le code**, pas par un signal. Il aurait pu tenir encore
des mois.

Cette US ne change rien à la politique d'envoi. Elle rend visible ce qui était
silencieux, et prévient quand ça dérape.

## Contexte constaté (pour l'implémentation)

L'outillage existe déjà, il n'y a rien à monter :
- un `Meter` applicatif (`Mssante.MailProcessing`), avec une convention de
  nommage de compteurs en `mssante_*_total` ;
- Prometheus qui collecte l'API, et des tableaux de bord Grafana provisionnés
  avec l'AppHost.

Tous les chemins d'omission journalisent déjà — ce qui manque est le comptage,
la distinction des motifs, et l'alerte.

## La distinction qui fait tout le travail

**Un en-tête absent n'est pas une anomalie.** Un message sans pièce jointe n'a
légitimement ni `X-MSS-CODECDA` ni `X-MSS-INS`. Un message qui ne vise pas Mon
Espace Santé n'a légitimement pas `X-MSS-MES`.

Un compteur qui mélange l'absence légitime et la dégradation ne sert à rien : il
noiera trois pannes par an dans des dizaines de milliers d'absences normales, et
personne ne le regardera. **Séparer les deux est l'exigence centrale de cette
US**, pas un raffinement.

Les cas à distinguer, tels qu'ils existent aujourd'hui dans le code :

| En-tête | Posé | Absent — légitime | Dégradé — à compter et alerter |
|---|---|---|---|
| `X-MSS-CODECDA` | archive IHE_XDM lue, au moins un code CDA | aucune PJ IHE_XDM | archive présente mais illisible ; archive lue mais 0 document CDA |
| `X-MSS-INS` | au moins un document CDA lu | aucune PJ IHE_XDM | mêmes cas que ci-dessus |
| `X-MSS-NIL` | numéro de produit configuré | *aucun* — il est exigé sur **tout** message sortant | numéro de produit non configuré |
| `X-MSS-MES` | blocage de réponse demandé **et** destinataire Mon Espace Santé | blocage non demandé | blocage demandé mais aucun destinataire Mon Espace Santé |

Plus un cas transverse, le plus grave : **l'injection échoue en bloc** et le
message part sans **aucun** des quatre en-têtes. Il doit être compté à part.

## Règles métier

1. **La politique d'envoi ne change pas.** Un en-tête qui ne peut pas être posé
   n'interrompt jamais l'envoi et n'est jamais signalé au praticien. Seul le
   compteur bouge.

2. **Chaque en-tête est compté par issue** : posé / absent légitimement /
   dégradé, avec le motif de la dégradation.

3. **Le taux se calcule sur le bon dénominateur.** Le taux de dégradation de
   `X-MSS-CODECDA` se rapporte aux messages **porteurs d'une archive IHE_XDM**,
   pas à tous les messages sortants. Rapporté à tous les messages, un incident
   grave resterait sous le bruit.

4. **Une alerte se déclenche sur dégradation.** Seuil initial : **toute**
   dégradation alerte. On ne fixe pas un seuil au doigt mouillé — on part de
   l'hypothèse qu'une dégradation est rare, et **si** la baseline montre un
   bruit de fond structurel, le seuil est relevé, avec la mesure qui le
   justifie consignée dans ce fichier.

5. **Aucune donnée de santé dans les étiquettes de métrique.** Ni adresse du
   praticien, ni nom de fichier, ni INS, ni contenu. Le code CDA
   (`34112-3`, `15508-5`…) est un **type de document**, pas une donnée patient :
   il est autorisé comme étiquette, et c'est même exactement la volumétrie que
   l'ANS cherche à suivre. Toute étiquette à cardinalité non bornée est
   interdite.

6. **Le tableau de bord répond à une seule question** : « depuis N heures,
   combien de messages sont partis non conformes, et pourquoi ». Un panneau par
   en-tête, plus le compteur d'échec global.

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 échec)
- [ ] Un compteur par en-tête, ventilé par issue (posé / absent légitime /
      dégradé) et par motif de dégradation
- [ ] Un compteur distinct pour l'échec global d'injection (message parti sans
      aucun en-tête)
- [ ] Test unitaire par cas du tableau ci-dessus : chaque chemin d'omission
      incrémente le bon compteur avec le bon motif
- [ ] Test unitaire : un message sans pièce jointe compte une **absence
      légitime**, jamais une dégradation (règle 3 — c'est le test qui protège
      l'utilité du signal)
- [ ] Test unitaire : un envoi nominal n'incrémente aucun compteur de
      dégradation
- [ ] Test : aucune étiquette de métrique ne porte d'adresse, de nom de fichier
      ou de donnée patient (règle 5)
- [ ] Tableau de bord Grafana provisionné avec l'AppHost, un panneau par en-tête
      + panneau d'échec global
- [ ] Règle d'alerte définie et documentée, avec son seuil initial et le
      protocole de calibration (règle 4)
- [ ] La politique d'envoi est inchangée : un test prouve qu'une dégradation
      n'empêche pas l'envoi (non-régression de la règle 1)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Démarrer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
   (profil `https`).
2. Ouvrir Grafana (`http://localhost:3000`) et vérifier que le tableau de bord
   « conformité en-têtes MSSanté » est provisionné et à zéro.
3. **Cas nominal** : envoyer un message avec une archive IHE_XDM valide portant
   un document CDA. **Attendu** : `X-MSS-CODECDA` et `X-MSS-INS` comptés
   « posés » ; aucune dégradation.
4. **Cas multi-documents** : envoyer une archive portant plusieurs CDA.
   **Attendu** : un seul message compté, en-tête multi-valué, aucune
   dégradation.
5. **Absence légitime** : envoyer un message **sans** pièce jointe.
   **Attendu** : `X-MSS-CODECDA` compté « absent légitime », **pas** dégradé.
   Le panneau de dégradation ne bouge pas.
6. **Dégradation** : envoyer un message avec une pièce jointe nommée comme une
   archive IHE_XDM mais volontairement corrompue (un fichier texte renommé).
   **Attendu** : le message **part quand même**, et le compteur de dégradation
   s'incrémente avec le motif « archive illisible ». C'est le test central de
   la US.
7. **Dégradation de configuration** : vider le numéro de produit convergence,
   redémarrer, envoyer un message. **Attendu** : `X-MSS-NIL` compté dégradé,
   motif « non configuré ». Remettre la valeur (`3734`) ensuite.
8. **Alerte** : vérifier que le cas 6 déclenche bien la règle d'alerte.
9. **Cardinalité** : relever le point de collecte `/metrics` et vérifier
   qu'aucune étiquette ne porte d'adresse MSSanté, de nom de fichier ni de
   donnée patient.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors périmètre fonctionnel DSR — exigence de supervision
  d'un socle MSSanté déjà référencé
- **Exigences DSR honorées** : aucune exigence DSR fonctionnelle nouvelle. La US
  **surveille** le respect d'exigences existantes du Référentiel socle MSSanté
  #2 — ECO.2.4.1 (§3.8.1, `X-MSS-CODECDA`), ECO.2.4.2 (§3.8.2, `X-MSS-INS`),
  ECO.2.4.3 (§3.8.3, `X-MSS-NIL`) et ECO.2.2.8 (§3.4.2.3, `X-MSS-MES`). **Le
  rattachement DSR précis est à confirmer avec le référent Ségur** — je ne cite
  pas de code d'exigence DSR que je n'ai pas vérifié.
- **INS** : la US **compte** l'indicateur `X-MSS-INS` (valeur O/N, présence
  d'une INS qualifiée dans le CDA). Elle ne lit, ne stocke et n'expose **aucun**
  matricule INS, aucun OID, aucun trait d'identité. Compter la proportion de
  documents émis sans INS qualifiée est précisément l'objectif que l'ANS assigne
  à cet en-tête (§3.8.2).
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel — inchangé,
  la US ne touche pas l'authentification.
- **Habilitations** : non applicable — les compteurs sont agrégés, jamais
  rattachés à un praticien.
- **Interop CI-SIS** : le code compté provient du champ `code` de l'en-tête CDA,
  volet Structuration Minimale de Documents de Santé [CI-STRU-ENTETE]. La US le
  **compte**, ne le transforme pas et ne le valide pas.
- **Tracé PGSSI-S** : les évènements d'omission et d'échec sont **déjà**
  journalisés ; la US ajoute leur comptage agrégé. Conservation des métriques
  alignée sur la rétention Prometheus de la plateforme, distincte de celle des
  journaux d'accès (6 ans).
- **Consentement patient** : non applicable.
- **Référentiels métier** : LOINC et codes CI-SIS apparaissent comme **valeurs
  d'étiquette** (type de document). Aucune validation terminologique n'est
  attendue de cette US.
- **Hébergement HDS** : oui — l'API héberge des DSCP. **La US ne doit créer
  aucun nouveau flux de DSCP** : les métriques sortent vers Prometheus, qui
  n'est pas un environnement HDS. D'où la règle 5, qui est ici une contrainte
  d'hébergement autant qu'une contrainte de cardinalité.
- **AIPD / impact RGPD** : inchangé, **sous réserve du respect de la règle 5**.
  Une étiquette portant l'adresse MSSanté du praticien créerait un traitement de
  données personnelles hors HDS et rendrait l'AIPD à reprendre.

## Notes pour le PO — hors périmètre assumé

Relevés en instruisant `X-MSS-CODECDA` le 2026-09-01, écartés de cette US :

- **Une seule archive IHE_XDM est lue par message** (la première trouvée). Un
  message qui en porterait deux perdrait les codes de la seconde. Le référentiel
  raisonne partout sur une archive par message, donc le cas est théorique — mais
  il est silencieux. Cette US le rendra visible s'il survient, sans le corriger.
- **Les codes ne sont pas dédupliqués** : deux CDA de même type donnent
  `34112-3,34112-3`. C'est **correct** — l'en-tête sert à suivre la volumétrie
  *et* le type de documents, donc une valeur par document. À ne pas « corriger »
  par réflexe.
