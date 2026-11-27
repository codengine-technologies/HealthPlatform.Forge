# Anneau de traitement — spécification fonctionnelle

> **Statut** : validée par le product owner le 2026-11-27 (« d'accord pour le reste, variante D »). Aucun code de
> production n'est écrit. Tasks rédigées : task-497, task-498, task-499 (EPIC E027).
> **Date** : 2026-11-27 — lecture du code à cette date (`api-mail`, `dtos-mss`, `client-angular`, `client-mobile`).
> **Maquettes** : [maquettes.html](maquettes.html) — **Challenge du design** : [revue-design.md](revue-design.md).

## 1. L'idée

Chaque message est un anneau incomplet. Chaque étape franchie remplit un segment, et le vide montre ce qui reste à
faire. Quand le message est traité, l'anneau se ferme.

Le médecin ne gère plus des messages, il gère des **boucles ouvertes**. L'anneau répond à quatre questions, chacune
par un code visuel distinct :

| Question | Code demandé | Code retenu après la revue de design (variante D) |
|---|---|---|
| Où en est-on ? | Les segments remplis | Les segments remplis |
| Dans quel sens ? | La pointe de l'arc et le sens de rotation | Le dossier et le libellé « Envoyé » |
| À qui le tour ? | Une balle, au centre ou dehors | Initiales **dans l'anneau** ; « Non affecté » et « Attente patient » écrits |
| Depuis combien de temps ? | Les cernes, trois au plus | Un compteur J+N, plein au dernier seuil |

La couleur ne dit que la **gravité clinique**. Aucun état ne repose sur la seule couleur.

Les règles de cette spécification (qui a un anneau, états, tour, ancienneté, gravité) valent pour toutes les
variantes visuelles. Le choix de la variante est la décision 14.

## 2. Ce que l'application sait déjà

L'EPIC E024 (« traiter, déléguer, boucler ») a livré la plupart des données que l'anneau doit montrer. L'anneau est
donc d'abord une **représentation**, pas un nouvel état.

| Besoin de l'anneau | Ce qui existe | Écart |
|---|---|---|
| Lu / non lu | `Mails.IsRead`, miroir du drapeau de la messagerie. **Partagé par toute la boîte**, pas par personne | Aucune date ni auteur de lecture sur le message (seulement au journal) |
| Traité | `MailHandlingStates` (task-454) : état, geste, auteur, date. Annulable 6 s, « Remettre à traiter » | Aucun |
| Qui est dans la boucle | Règle « à traiter » : message **suivi** (arrivé depuis la date de début du suivi, task-466) et non « Pour info » (task-456), hors Envoyés, Brouillons, Corbeille | Aucun |
| Affectation | `MailAssignments` (task-457) : une personne, auteur, date ; initiales sur la ligne ; vue « Pour moi » | Aucun |
| Acquittement de biologie | `BiologyAcks`, **par document**, en ajout seul. Cinq actions : Pris connaissance, Rappel patient, Convocation, Adressage confrère, Marquer comme résolu. Réclamé **seulement** pour un compte rendu avec anomalie | La ligne de liste ne porte que le nombre d'acquittements en attente, pas l'action la plus récente |
| Anomalie | Indicateur du laboratoire (`IsFlagged`, code d'interprétation). Critique = LL, HH, AA | task-467 ouverte : certains codes sont manqués |
| Date d'arrivée réelle | `Mails.ArrivalDate` (task-466) | Aucun |
| Messages sans action attendue | Tag système « Pour info » (copie seule, message automatique) ; accusés et rapports détectés (`IsReport`) | Aucun |
| État d'un envoi | Envoyé, distribué, non distribué, lu (task-487) | Les rapports ne sont classés **qu'à l'ouverture d'une conversation** ; rien dans la liste |
| Attente de réponse | **Rien.** task-462 a été annulée le 2026-11-21 | Tout |
| Ancienneté, retard, échéance | **Rien** | Tout |
| Compteurs | « À traiter » par dossier et par tag, « Pour moi », résumé « Bio à acquitter » : calculés par requête à chaque appel, sans agrégat | Pas de ventilation par ancienneté |
| Mise à jour en direct | Évènements poussés après « traité » et après une attribution | Aucun évènement pour un acquittement intermédiaire |
| Tableau de bord | Web : `/messagerie/dashboard`, tuiles par drapeau. Mobile : onglet Accueil, sept tuiles | Une tuile de plus |
| Préférences | Par personne : `UserSettingsDto`. Par boîte : identité d'expéditeur, date de début du suivi | Aucune légende |

Trois choses demandées n'ont **aucune** donnée aujourd'hui : l'étape « patient vu », l'attente d'une réponse à un
envoi, et le retard.

## 3. Qui a un anneau

Un message a un anneau ouvert quand il est **« à traiter »** au sens de la règle existante
(`MailHandlingRule`), sans changement :

1. jamais dans Envoyés, Brouillons ou Corbeille ;
2. un compte rendu de biologie à acquitter garde le message « à traiter », où qu'il soit rangé ;
3. sinon l'état posé à la main décide (« Traité », « Remettre à traiter ») ;
4. sinon : le message est suivi **et** n'est pas « Pour info ».

Un message traité a un anneau fermé. Les autres sont **hors suivi** : « Pour info », accusés et rapports, messages
antérieurs à la date de début du suivi. Ils n'ouvrent pas de boucle et ne comptent nulle part.

## 4. Machines à états

### 4.1 Courrier et message — reçu → lu → traité

| État | Segments | Condition |
|---|---|---|
| Reçu | 1 sur 3 | À traiter, non lu |
| Lu | 2 sur 3 | À traiter, lu |
| Traité | fermé | `MailHandlingStates.State = Handled` |

| Transition | Déclencheur (existant) | Trace |
|---|---|---|
| → Reçu | Synchronisation d'un message suivi, non « Pour info » | acte système |
| Reçu → Lu | Ouvrir le message ou son fil, « Marquer comme lu », ou lecture depuis un autre logiciel | `MailRead`, au nom de la personne |
| Lu → Reçu | « Marquer comme non lu » | `MailRead` |
| Reçu ou Lu → Traité | Bouton « Traité », répondre, transférer, ranger hors de la Boîte de réception, rattacher à un patient, import Weda, traitement groupé, « traité avec le fil » | `MailMarkedHandled` + geste |
| Traité → état d'avant | « Annuler » (6 s) | `MailMarkedToHandle` |
| Traité → Lu | « Remettre à traiter » | `MailMarkedToHandle` |
| Hors suivi → Lu | « Remettre à traiter » sur un message hors suivi | `MailMarkedToHandle` |

Traiter marque aussi le message lu ; lire ne le traite pas.

### 4.2 Biologie sans anomalie

Aucun acquittement n'est réclamé pour un compte rendu sans anomalie (l'API le refuse). Il suit donc l'anneau du
courrier : reçu → lu → traité. « Traiter les résultats sans anomalie » ferme ces anneaux d'un geste.

### 4.3 Biologie avec anomalie — reçu → pris connaissance → suite donnée → résolu

L'anneau lit l'acquittement existant. Aucune saisie nouvelle.

| État | Segments | Condition (dernière action du compte rendu) | À qui le tour |
|---|---|---|---|
| Reçu | 1 sur 4 | Aucune action | La boîte |
| Pris connaissance | 2 sur 4 | Pris connaissance | La boîte |
| Suite donnée | 3 sur 4 | Rappel patient, Convocation ou Adressage confrère | Un tiers : le patient ou le confrère |
| Résolu | fermé | Marquer comme résolu | — |

- L'état suit la **dernière** action, comme aujourd'hui (« Dernière action : … »). Une action peut sauter une étape :
  « Rappel patient » sur un compte rendu jamais acquitté remplit trois segments d'un coup.
- « Marquer comme résolu » sur le dernier compte rendu en attente traite le message (geste existant).
- « Traité » n'acquitte jamais une biologie. Inchangé.
- Un compte rendu antérieur au suivi est hors suivi.

**Alternative demandée** : reçu → patient contacté → patient vu → traité. Elle demande une action « patient vu » qui
n'existe pas, donc une donnée clinique nouvelle à saisir et à tracer. Elle laisse aussi deux segments vides pour une
anomalie qui ne demande aucun contact (décision 11).

### 4.4 Message envoyé — envoyé → distribué → lu → répondu

Sens inverse. Cette machine dépend d'un arbitrage (décision 9).

| État | Segments | Condition | Donnée |
|---|---|---|---|
| Envoyé | 1 sur 4 | Message envoyé | Existe |
| Distribué | 2 sur 4 | Rapport de distribution reçu | Existe, mais classé seulement à l'ouverture d'une conversation |
| Lu | 3 sur 4 | Accusé de lecture reçu | Idem |
| Répondu ou clos | fermé | Réponse reçue, ou clôture à la main | **N'existe pas** |
| Non distribué | anneau en échec | Rapport d'échec | Existe, même limite |

Aujourd'hui un message envoyé n'est jamais « à traiter ». Lui donner une boucle ouverte, c'est rouvrir le sujet de
task-462.

## 5. À qui le tour

Règle, dans l'ordre :

1. **Un tiers** : la dernière action de biologie est Rappel patient, Convocation ou Adressage confrère ; ou un envoi
   attend sa réponse.
2. **Une personne de la boîte** : l'attribution est ouverte. C'est « moi » si elle m'est attribuée, sinon les
   initiales du collègue. Une personne dont l'accès est retiré garde ses initiales, barrées.
3. **Sans attribution** :
   - la boîte n'a qu'une personne active : c'est « moi » ;
   - la boîte a plusieurs personnes : « personne », et cela se voit.

« Moi » dépend de la personne qui regarde : le même message montre le point chez l'un et des initiales chez l'autre.
Le signe « non affecté » ne s'affiche jamais dans une boîte à une seule personne, où il serait présent sur toutes les
lignes.

## 6. Ancienneté

- L'ancienneté se calcule **à l'affichage**, par différence entre maintenant et une date de référence, comparée à
  trois seuils. Rien n'est écrit périodiquement en base.
- **Date de référence proposée** : l'ouverture de la boucle, c'est-à-dire la date d'arrivée réelle, ou la date de
  « Remettre à traiter » si le message a été rouvert. Pour un envoi : la date d'envoi. Motif : une date remise à zéro
  à chaque étape ferait paraître récent un message de quinze jours qui vient d'être lu (décision 13).
- **Seuils proposés**, en jours calendaires, par catégorie (décision 5) :

| Catégorie | 1er seuil | 2e seuil | En retard |
|---|---|---|---|
| Biologie, valeur critique | 4 h | 24 h | 72 h |
| Biologie avec anomalie | 1 j | 3 j | 7 j |
| Courrier | 3 j | 7 j | 14 j |
| Envoyé | 7 j | 14 j | 30 j |

- La valeur critique a ses seuils en **heures**. Avec des seuils en jours, un potassium à 6,1 non acquitté depuis
  24 heures ne serait « en retard » qu'au septième jour (décision 16).

- Un anneau fermé ou hors suivi n'affiche aucune ancienneté.

## 7. Gravité

- Neutre : pas d'anomalie. Ambre : anomalie (L, H, A). Rouge : valeur critique (LL, HH, AA).
- L'anomalie est le jugement du laboratoire, jamais une comparaison aux bornes (règle du 2026-10-26).
- La couleur est doublée de la pastille ⚠ n existante : contour pour anormal, pleine pour critique.
- Une ligne traitée garde sa pastille ⚠ n, atténuée : fermer la boucle n'efface pas l'anomalie.
- Un envoi non distribué n'est pas une gravité clinique : croix et « Non distribué », en teinte neutre.
- Dépendance : task-467 (anomalies manquées par la liste fermée des codes). Tant qu'elle est ouverte, un anneau
  peut être neutre à tort.

## 8. Droits et traçabilité

- L'anneau n'ajoute **aucun acte**. Chaque geste qui le fait avancer existe et est déjà tracé au nom de son auteur
  réel (règle 14).
- Tout ce que montre l'anneau appartient à la boîte et est vu de toutes les personnes rattachées et actives.
- Rouvrir : « Remettre à traiter », par toute personne active de la boîte, tracé. Inchangé.
- Seul acte nouveau : **changer les seuils d'ancienneté de la boîte**, tracé au nom de son auteur avec l'ancienne et
  la nouvelle valeur, comme la date de début du suivi.
- Les réglages d'affichage appartiennent à la personne et ne sont pas tracés.
- L'infobulle décrit l'état, jamais le patient : ni nom, ni INS, ni valeur.

## 9. Cas particuliers

| Cas | Comportement |
|---|---|
| Message avec plusieurs comptes rendus | Liste : un anneau par message, commandé par le compte rendu le moins avancé. Détail : un anneau par compte rendu |
| Résultat partiel puis complet | Règle existante : une nouvelle version est un nouveau document. Nouvel anneau ; l'ancienne version sort des boucles ouvertes (à vérifier dans le code) |
| Fil de conversation | Chaque message a son anneau. « Traité » ferme aussi les précédents du fil, jamais un plus récent (task-493) |
| Réaffectation | Le centre change. L'historique est au journal et dans le détail (« attribué par … le … ») |
| Transfert | Transférer traite le message reçu (geste existant). Le transfert est un envoi : il suit la décision 9 |
| Rangé hors de la Boîte de réception | Ranger traite le message (décision humaine du 2026-11-12). Exception existante : une biologie à acquitter reste une boucle ouverte dans son dossier |
| Corbeille | Hors boucle |
| Message revenu après un incident | L'état suit le message (ancrage task-453) |
| Hors ligne | L'anneau se dessine sur les données locales. Un délégataire ou un membre sans verdict de l'opérateur ne voit rien (règle 14) |

## 10. Intégration dans les écrans

**Liste (web et mobile)**
- L'anneau prend la place de l'initiale de l'expéditeur, à gauche. Le gras, le liseré et le point « non lu » restent.
- La personne peut revenir à l'icône classique (préférence).
- Infobulle au survol sur le web, appui long sur mobile, comme pour l'icône « répondu ».
- **Décision du product owner du 2026-11-27** : quand un message est « à traiter par » quelqu'un, ses initiales
  s'affichent **à l'intérieur de l'anneau**. La pastille d'initiales posée par task-457 est **supprimée** de la ligne
  et du détail, sur le web et sur mobile : l'anneau la remplace.
  - Initiales sur fond plein quand le message m'est attribué, initiales seules pour un collègue, barrées si son accès
    est retiré.
  - Avec l'icône classique (préférence), la pastille d'initiales revient : sans anneau, c'est le seul signe.
  - Le texte « À traiter par … — attribué par … le … » du détail reste : il dit qui a attribué et quand.
- Variante D : la pastille ⚠ n reste. S'ajoutent « Non affecté », « Attente patient » et J+N. La pastille « Traité »
  est remplacée par la coche de l'anneau.

**Détail**
- Grand anneau en tête, étapes légendées avec date et auteur quand ils existent.
- Web : les boutons d'acquittement sont aujourd'hui dans le panneau latéral « Actions & dossier », et « Traité » dans
  la barre d'outils. Mobile : ils sont dans l'onglet Biologie. Les placer sous l'anneau **déplace des repères** : à
  trancher (décision 14).

**Tableau de bord**
- Une tuile « Boucles ouvertes » sous drapeau `dashboard_widget_open_loops`, sur le web et sur mobile.
- Total, « en retard », puis par groupe : biologies à acquitter, non lus, lus à traiter, non affectés, pour moi.
- Chaque ligne ouvre la liste filtrée. Web : nouveaux paramètres d'adresse. Mobile : extension de l'intention
  d'entrée de la boîte de réception.
- Elle recoupe les tuiles « À traiter », « Pour moi » et « Bio à acquitter ». Alternative : ne pas la créer, ajouter
  « dont N en retard » à ces trois tuiles, et créer la seule tuile « Non affectées » (décision 7).

**Préférences**
- Par personne : anneau ou icône classique ; éléments affichés (affectation, attente d'un tiers, gravité,
  ancienneté, animations) ; contraste renforcé. Le contraste par défaut est déjà conforme.
- Par boîte : seuils d'ancienneté.
- Légende dessinée par le composant réel, avec les seuils en vigueur. Accessible depuis la tuile.

`client-blazor` est hors périmètre : aucune des fonctions d'E024 n'y existe.

## 11. Données et performances

**Liste : aucun état d'anneau à persister.** La ligne (`MailDto`) porte déjà `IsRead`, `ArrivalDate`, `Handling`,
`Assignment`, `HasAbnormalBiology`, `PendingBiologyAcksCount` et `HasCriticalPendingBiologyAck`.

- Courrier : l'anneau se dessine sans aucun champ nouveau.
- Biologie avec anomalie : il manque un champ, l'avancement d'acquittement du compte rendu le moins avancé. Il se
  calcule dans la lecture groupée qui existe déjà (`EnrichManyWithBiologyAcksAsync`), sans aller-retour de plus.
- Ancienneté : calculée par le client à partir de `ArrivalDate` et des seuils, lus une fois avec les réglages.

Une colonne « état d'anneau » recopierait une vérité tenue à quatre endroits : le drapeau « lu », que d'autres
logiciels modifient, l'état « traité », l'attribution et les acquittements. Il faudrait la tenir à jour dans la
synchronisation, les déplacements et le retour d'un message après incident. Le risque est un anneau qui ment. **Ne
pas la créer, sauf si la mesure le demande.**

**Compteurs de la tuile**
- Les compteurs « À traiter » et « Pour moi » sont déjà recalculés par requête à chaque appel de la liste des
  dossiers, sans agrégat. La tuile ajoute une ventilation par groupe et par palier d'ancienneté, sur le même ensemble.
- **Mesurer avant de choisir** (règle d'or 5) : coût de ces requêtes sur une boîte de 10 000 messages, avant et
  après. Si le coût monte, la réponse est un index partiel sur les boucles ouvertes, puis un agrégat tenu à jour, dans
  cet ordre.
- La tuile a son propre appel, hors du chemin de la liste des messages.

**Transactions** : chaque geste écrit déjà son état dans sa transaction. L'anneau étant dérivé, rien ne s'ajoute.

**Migration** : aucune reprise de données si l'anneau est dérivé. Les messages antérieurs au suivi restent hors
suivi. Seule migration : les seuils de la boîte, en ajout, avec leurs valeurs par défaut.

**Mise à jour en direct** : « traité » et l'attribution poussent un évènement aux autres personnes connectées. Un
acquittement intermédiaire (Pris connaissance, Rappel patient, Convocation, Adressage confrère) n'en pousse aucun ;
seul « Résolu » le fait, par le « traité » qu'il déclenche. Il faut l'ajouter, sinon l'anneau d'un collègue reste en
retard d'une étape jusqu'au rechargement.

## 12. Incohérences relevées dans l'existant

1. **Deux définitions de « biologie à acquitter ».** Le résumé du tableau de bord ne compte que la Boîte de réception
   et ses sous-dossiers. La règle « à traiter » compte un compte rendu en attente dans tout dossier. Une biologie
   rangée ailleurs est comptée d'un côté, pas de l'autre. La tuile doit n'en garder qu'une.
2. **Rapports d'envoi lus à la demande.** Distribué, lu et non distribué ne sont connus qu'après l'ouverture d'une
   conversation. Un anneau d'envoi dans la liste demande de les classer à la synchronisation.
3. **« Lu » est partagé.** Le segment « lu » veut dire « lu par quelqu'un de la boîte », pas « lu par moi ».
4. **Lecture sans date ni auteur sur le message.** Le détail ne peut dater l'étape « lu » qu'en lisant le journal.
5. **task-467** : anomalies manquées.

## 13. Décisions

> **Validées le 2026-11-27.** Le product owner a retenu la variante D, a demandé les initiales à l'intérieur de
> l'anneau avec suppression de la pastille d'initiales, et a accepté les recommandations ci-dessous pour le reste.
>
> Deux points n'avaient pas de recommandation tranchée ; la forge les a lus ainsi, à confirmer avant `/start` :
> - **7 — tableau de bord** : enrichissement des tuiles existantes et tuile « Non affectées » (préférence de la
>   revue), pas de tuile unique « Boucles ouvertes ». Écrit dans task-499 ;
> - **15 — EPIC** : nouvel EPIC E027 « Anneau de traitement : voir les boucles ouvertes ».
>
> L'épreuve avec trois à cinq médecins (décision 14) n'a pas été faite : la variante D est retenue sans elle.

| N° | Question | Recommandation |
|---|---|---|
| 1 | Messages insignifiants | Garder la règle existante : « Pour info », accusés, rapports et messages antérieurs au suivi sont hors suivi, sans boucle, hors compteurs. Pas de règles par personne |
| 2 | Plusieurs résultats ou patients | Un anneau par message dans la liste, un par compte rendu dans le détail |
| 3 | Partiel puis complet | Nouvel anneau (règle existante) |
| 4 | Réouverture | Règle existante : toute personne active de la boîte, tracé |
| 5 | Seuils | Par catégorie, réglés au niveau de la boîte ; valeurs du § 6 |
| 6 | Segments du courrier | Trois. « Affecté » dit qui, pas où l'on en est ; « répondu » est un geste qui ferme |
| 7 | Périmètre du tableau de bord | La boîte, plus « Pour moi ». Choisir entre une tuile « Boucles ouvertes » et l'enrichissement des trois tuiles existantes, plus « Non affectées ». La revue préfère l'enrichissement |
| 8 | Niveaux de réglage | Personne : affichage. Boîte : seuils. Aucun niveau « établissement » n'existe dans le produit |
| 9 | Messages envoyés | À arbitrer : task-462 a été annulée. Proposition : un lot séparé, limité à l'état d'acheminement (distribué, lu, non distribué), sans attente de réponse |
| 10 | Archivé non traité | Règle existante : ranger traite, sauf la biologie à acquitter, qui reste une boucle ouverte |
| 11 | Segments de la biologie | Alignés sur l'acquittement existant, sans action « patient vu » |
| 12 | Biologie sans anomalie | Anneau du courrier |
| 13 | Date de référence de l'ancienneté ; jours calendaires ou ouvrés | Ouverture de la boucle ; jours calendaires |
| 14 | Variante visuelle, et place des boutons d'acquittement | Variante D, après épreuve avec trois à cinq médecins contre B et l'écran actuel. Boutons sous l'anneau, rangés par étape. **Tranché le 2026-11-27 pour l'affectation** : initiales dans l'anneau, pastille d'initiales supprimée |
| 15 | EPIC | Nouvel EPIC E027, ou suite d'E024 |
| 16 | Seuils d'une valeur critique | En heures : 4 h, 24 h, 72 h |
| 17 | Réglages d'affichage | Un par élément, comme demandé ; la revue conseille « tout ou rien » pour que tout le cabinet voie les mêmes signes |
| 18 | Biologie antérieure au suivi | Règle de task-466 inchangée : elle ne réclame rien. Cercle pointillé « hors suivi », avec un ⚠ atténué si elle porte une anomalie ; mention « Antérieur au suivi » dans le détail |

## 14. Découpage

| Lot | Task | Contenu | Repos |
|---|---|---|---|
| 1 | task-497 | L'anneau dans la liste et le détail : courrier et biologie, infobulle, accessibilité, préférence « anneau ou icône classique » | api-mail, dtos-mss, client-angular, client-mobile |
| 2 | task-498 | Ancienneté : seuils de la boîte, compteur J+N, éléments affichés, contraste renforcé, légende | api-mail, dtos-mss, client-angular, client-mobile |
| 3 | task-499 | Tableau de bord : « dont N en retard », tuile « Non affectées », listes filtrées, après mesure | api-mail, dtos-mss, client-angular, client-mobile |
| 4 | non rédigée | Messages envoyés : hors de ce lot (décision 9) | api-mail, dtos-mss, client-angular, client-mobile |

Prérequis conseillé : task-467.

## 15. Conformité santé

- **Données de santé** : aucune donnée nouvelle. L'anneau affiche des états déjà stockés dans la base de la boîte.
  Hébergement inchangé.
- **INS** : non concerné.
- **Authentification, habilitations** : inchangées. Un délégataire ou un membre ne voit les anneaux qu'avec un verdict
  récent de l'opérateur.
- **Traçabilité** : un seul acte nouveau, le changement des seuils de la boîte, conservé comme les autres actes.
- **Journaux et notifications** : aucun contenu clinique dans l'infobulle, les compteurs ou les journaux.
- **Interopérabilité, consentement** : non concernés.
- **AIPD** : inchangée tant qu'aucune étape clinique n'est ajoutée. À revoir si « patient vu » est retenu
  (décision 11).
