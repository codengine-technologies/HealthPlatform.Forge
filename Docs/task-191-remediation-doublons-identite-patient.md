# task-191 — Dossiers patients en doublon sur une même identité : note de remédiation

> **Statut : remédiation NON exécutée, en attente d'arbitrage humain.**
> Rattachée à [`questions/task-183.md`](../questions/task-183.md), question 3
> (décisions 3.2 « protocole » et 3.3 « qui porte l'acte »).

## Ce qui a été corrigé, et ce qui ne l'a pas été

task-191 empêche la **création** de nouveaux doublons : l'index unique
`UX_MailPatients_Ins_Oid` sur `("Ins", COALESCE("Oid", ''))` refuse un second
dossier pour la même identité (matricule, domaine d'attribution), et l'ingestion
qui perd la course est rejouée sur le dossier gagnant.

Les doublons **déjà présents** ne sont ni fusionnés ni supprimés. Réunir deux
dossiers déplace des documents cliniques, des oppositions MSS et des traits
d'identité : c'est un acte d'identito-vigilance, pas un effet de migration.

## Ce qu'il se passe sur une base qui porte déjà des doublons

La migration `20260929120000` tourne par praticien, au premier accès. Sur une
base qui porte au moins une identité en doublon :

- elle **n'installe pas** l'index, sans échec (un échec rendrait la messagerie
  du praticien inaccessible) ;
- elle émet un `WARNING` PostgreSQL, sans valeur de matricule ;
- elle est marquée appliquée : elle ne sera **pas** rejouée d'elle-même.

Cette base garde le comportement d'avant la task, ni pire ni corrigé : de
nouveaux doublons y restent possibles sous concurrence jusqu'à la remédiation.

## Protocole proposé (à valider)

1. **Inventorier** chaque base praticien avec
   `Api/Mail/docs/task-191-inventaire-doublons-identite-patient.sql` (lecture
   seule). Commencer par le bloc de dénombrement en fin de fichier. La sortie ne
   contient ni matricule ni nom : elle peut quitter la production.
2. **Qualifier la portée** avec le DPO (mise à jour de l'AIPD : art. 5.1.d,
   exactitude des données). La portée se mesure en identités en doublon et en
   documents rattachés (`documents_rattaches`), base par base.
3. **Décider** du protocole de réunion (question 3.2) et de son porteur (3.3) :
   validation par le praticien, traçabilité attendue dans le journal d'audit.
   Le dossier conservé par défaut serait le plus ancien (`dossiers_ids[1]`) :
   c'est celui que l'ingestion retient déjà pour un document sans domaine.
   Points à trancher : les oppositions MSS divergentes entre les deux lignes
   (la plus protectrice l'emporte ?) et les traits d'identité divergents.
4. **Réunir** les dossiers selon ce protocole, dans une task dédiée.
5. **Installer l'index** différé : instruction donnée en fin du fichier
   d'inventaire, à rejouer une fois que la requête principale ne rend plus
   aucune ligne. Elle échoue sans rien modifier s'il reste un doublon.

## Hors périmètre de cette note

- Deux dossiers du même matricule dans deux domaines **différents** (NIA et
  NIR) : deux identités distinctes au sens de task-183. Ils ne sont pas remontés.
- La réunion de dossiers NIA/NIR d'une même personne (matricules différents) :
  c'est l'autre volet de la question 3 de task-183.
