# Messagerie MSSanté : ce qui manque pour qu'un médecin l'aime

> **Analyse du 2026-11-11.** Inventaire de notre produit, recherche documentaire sur le marché français,
> les réseaux étrangers, les clients mail grand public et libres, et les besoins exprimés par les
> professionnels de santé. Les sources sont en fin de document.
>
> **Force de la preuve** : ●●● forte (étude, document officiel lu en entier) · ●● moyenne (presse,
> extrait, petit échantillon) · ● faible (témoignage isolé, affirmation d'éditeur). Ce qui relève de
> **notre inférence** est signalé *(inférence)*.
>
> **Notre statut** : tel qu'il ressort des EPICs et du code au 2026-11-11. « Livré » veut dire
> **mergé sur `develop`**, et **rien n'est encore en production** (E020 §7).

---

## 1. En une page

**Le diagnostic.** Le médecin ne souffre pas d'*envoyer* des messages : il souffre de **recevoir,
trier, intégrer et ne rien rater**. Ses messages viennent des laboratoires, de l'hôpital et de la
radiologie, et un confrère lui écrit rarement : seuls 14 % utilisent la messagerie sécurisée pour
joindre un soignant, contre 39 % le téléphone (URPS Centre-Val de Loire 2024, ●●●). Les pouvoirs
publics nomment les mêmes irritants (séminaire DNS/ANS/CNAM, janvier 2024, ●●●) : intégration au
dossier, doublons, formats illisibles, biologie non reçue ou en retard, données structurées perdues.
Les médecins disent « on s'y perd », « une heure par jour », « peur médico-légale d'avoir raté un
document ».

**Ce que dit la recherche internationale** sur la charge de la boîte du médecin (●●●) :
- les gains mesurables en volume viennent de **trois leviers** :
  - **supprimer** ce qui n'a pas de valeur clinique (copies, « pour info », notifications) ;
  - **router hors du médecin** (secrétariat, protocoles) ;
  - **dédoublonner** ;
- l'IA de rédaction réduit la **charge mentale**, pas le temps (Garcia, JAMA Netw Open 2024) ;
- les plages horaires dédiées, seules, ne marchent pas ;
- les médecins demandent quatre choses : **prioriser**, **moins de messages sans impact**,
  **faire entrer le personnel dans le tri**, **régler soi-même ce qu'on reçoit** (Murphy 2019).

**Où nous en sommes.** Sur la **lecture**, notre produit est déjà au-dessus du marché :
- une **vue centrée patient** : tous ses documents (biologie, prescriptions, comptes rendus…) et
  l'historique de ses valeurs de biologie ;
- une **classification automatique** de chaque document reçu (patient, type, auteur, priorité IA) ;
- CDA et HPRIM rendus, biologie structurée avec anomalies, acquittement en cinq actions ;
- **une IA sur les messages reçus.** Aucun client MSSanté concurrent n'en propose publiquement :
  - synthèse et résumé du jour ;
  - **chat qui cite ses sources et prépare des actions** (répondre, appeler le patient, lui envoyer
    un SMS, contacter un confrère) ;
  - modèles générés par l'IA ;
  - correcteur orthographique IA ;
- une **recherche sémantique**, en plus d'un plein texte fiable ;
- une **délégation en un clic** sous **traçabilité avancée** : chaque acte imputé à son auteur
  réel, journal de la boîte, audit sur 10 ans.

**Ce qui nous manque est la couche *flux de travail*** : transformer la boîte en **file de travail**
qui se vide. Elle comprend :
- un statut « traité » distinct du « lu » ;
- « à revoir le… » ;
- des vues par nature de document ;
- la délégation au secrétariat ;
- le suivi des envois ;
- les notifications mobiles ;
- l'intégration au dossier, en pause côté Weda.

**Les 12 manques qui comptent le plus**, par valeur attendue :

| # | Manque | Pourquoi | Statut | Effort *(inférence)* |
|---|---|---|---|---|
| 1 | **Intégration au dossier Weda en un geste** (E019 F3-F5 côté Weda ; tasks 358-361 en pause) | Douleur n° 1 partout (●●●). Leçon allemande : la KBV ne recommande son propre client mail que pour des tests, faute de transfert automatique vers le dossier patient | Partiel, en pause | M (côté Weda) |
| 2 | **Statut « Traité »** distinct de « lu », imputé et horodaté, avec la vue « reste à traiter » | Le médecin raisonne en « pris en charge ou non » (Whittaker, Grevet ●●●) ; la peur de rater un document (●●) | Absent (l'acquittement n'existe que pour la biologie) | M |
| 3 | **Vues par nature** : Biologie, Courriers et comptes rendus, Patients, Pour info, avec regroupement (« 12 résultats normaux du labo X → tout traiter ») | Ce sont les messages générés par les machines qui pèsent (Tai-Seale ●●●). HEY, Gmail et Apple le font | Partiel (types médicaux dans la recherche, étiquettes IA) | M |
| 4 | **Notifications push mobiles**, sobres : seuls les critiques déclenchent un son, et un résumé à heures fixes | Une app mobile sans push n'est pas consultée. La sobriété est prouvée (Kushlev, Mark ●●●) | **Absent** (hors périmètre E012) | M |
| 5 | **Pré-tri par le secrétariat** : file « à trier », affectation à un praticien, commentaires internes, alerte si un collègue est déjà sur le même message | Le meilleur levier de volume (−80 % de courrier chez le médecin au Royaume-Uni ●● ; −16 % et −62 % de doublons au Michigan ●●). C'était un irritant ANS n° 2 | L'**accès** est livré : bascule en un clic, BAL de cabinet, imputation (E020). Le **travail à plusieurs** dans la boîte est absent (F010 et F012 à 0 %) | L |
| 6 | **« À revoir le… »** (report et rappel) et **« relancer si pas de réponse »** sur un envoi | Les mails différés sont quotidiens et contournés par « non lu » (Sarrafzadeh ●●●). La boucle non fermée est un risque de soins | Absent | S-M |
| 7 | **Résultat de biologie → décision → tâche** : « rien à faire / revoir le patient / revoir en urgence », jusqu'à « résultat communiqué » | Modèle australien Best Practice et HotDoc (●●●). Prolonge notre acquittement | Partiel (5 actions sans échéance ni file de suivi) | M |
| 8 | **Suivi des envois** : délivré, lu, échec ; **avis de non-remise en français** ; adresse signalée comme « a déjà échoué » | 45 % des adresses de l'annuaire sont inactives (ANS 07/2026 ●●●). Le référentiel 1.7 impose DSN et NDR en français. Lifen est seul à le faire, côté hôpital | Partiel (≈ 30 %) | M |
| 9 | **Réponse d'absence avec un remplaçant nommé** | Réponse automatique RFC 3834 au référentiel 1.7. eHealthBox, Epic et Cerner le font (●●●) | Absent | S (si l'opérateur expose Sieve) |
| 10 | **Priorité expliquée** : « Urgent — pourquoi ? K⁺ 6,8 mmol/L » | Une priorité opaque détruit la confiance : Apple a classé des mails d'hameçonnage « prioritaires » (●●). En santé, elle engage la responsabilité | **Déjà fait**, constaté dans le code le 2026-11-11 : le motif de l'IA (`TagDto.UrgencyExplanation`) s'affiche en bandeau sur la ligne, sur le web et le mobile. Il reste à dater la décision et à laisser le praticien la corriger | S |
| 11 | **Messagerie patient (Mon espace santé) complète** | 58 % des généralistes échangent déjà hors consultation avec leurs patients, par téléphone ou e-mail (DREES ●●●). Le cadre MES protège : le médecin initie et clôt l'échange | Partiel (≈ 10 %) | M |
| 12 | **Une seule biologie par résultat**, quel que soit le canal (Apicrypt HPRIM et MSSanté CDA) | « On perd du temps à lire des choses en double » (●●●). Le palier 2 impose PDF + HPRIM + CDA dans un même envoi | Partiel : HPRIM×HPRIM détecté ; HPRIM et CDA donnent deux séries (task-390) | M |

---

## 2. Ce que vivent les médecins, et où nous en sommes

### Échelle du score

Le score mesure jusqu'où **notre messagerie IA** traite chaque douleur, sur `develop` au 2026-11-11.

| Score | Signification |
|---|---|
| **1** | Rien ne la traite. |
| **2** | Amorcée : quelques fonctions l'effleurent, mais la douleur reste entière. |
| **3** | À moitié : les fonctions existent, mais incomplètes ou hors du geste quotidien. |
| **4** | Largement traitée : il reste des manques secondaires. |
| **5** | Résolue de bout en bout. |

> **Rien n'est en production.** Un 5 se lit donc : résolu sur `develop`, à confirmer en recette puis en
> production. Les douleurs sont classées par force de preuve ; le détail des sources est au § 9.

### Vue d'ensemble

| # | Douleur | Preuve | Score | Où nous en sommes |
|---|---|---|:-:|---|
| 1 | Le document n'entre pas tout seul dans le dossier | ●●● | **2** | Rattaché au bon patient **dans la messagerie** ; l'import réel dans Weda est en pause |
| 2 | Biologie illisible, en double, valeurs structurées perdues | ●●● | **4** | Lue, structurée, anomalies, tendances, acquittement ; reste le doublon entre canaux |
| 3 | Trop de messageries, doublons entre elles | ●●● | **2** | Toutes les BAL MSSanté sous une seule connexion ; Apicrypt reste à part |
| 4 | Trouver le bon destinataire | ●●● | **3** | Recherche dans l'annuaire excellente ; rien ne dit quelle adresse fonctionne |
| 5 | Le canal sert à recevoir, pas à échanger | ●●● | **2** | Envoi complet, mais rien ne rend l'échange plus léger qu'un coup de fil |
| 6 | Pas de boîte de cabinet, pas de délégation à la secrétaire | ●●● | **5** | Livré : bascule en un clic entre sa boîte et celle d'un médecin, BAL de cabinet, imputation |
| 7 | Volume, saturation, peur de rater | ●● | **2** | L'IA aide à **voir** l'important ; rien n'aide à **vider** la boîte (sauf la biologie) |
| 8 | Messagerie patient : besoin réel, peur d'être submergé | ●●● | **2** | Garde-fous d'envoi faits ; Mon espace santé à ≈ 10 % |
| 9 | Ergonomie : sortir du logiciel, clics, « moche » | ●● | **4** | Intégrée à Weda, interface refondue ; enregistrer une PJ dans le dossier demande encore des clics |
| 10 | Impossible d'écrire hors MSSanté | ●● | **1** | Rien (l'espace de confiance l'interdit) |
| 11 | Lettres de sortie en retard ou absentes | ●● | **1** | Hors de portée d'un client : c'est l'émetteur qui retarde |
| 12 | Paramédicaux absents de la MSSanté | ●● | **2** | Annuaire et photo disponibles ; pas d'instantané ni de notification push |

**Moyenne : 2,5 / 5.** Nous sommes forts sur ce que le produit maîtrise seul : la lecture de la
biologie (4), l'ergonomie (4) et l'accès partagé (5). Nous sommes faibles sur trois fronts :
- le **flux de travail quotidien** (douleur 7) ;
- l'**intégration au dossier**, qui attend Weda (douleur 1) ;
- ce qui dépend d'autres acteurs (douleurs 3, 10 et 11).

**Les deux plus gros sauts au moindre effort** *(inférence)* :
- la douleur 7 passe de 2 à 4 avec l'horizon 1 : « Traité », « À revoir le… », vues par nature,
  priorité expliquée ;
- la douleur 1 passe de 2 à 4 en reprenant la partie Weda d'E019.

### Le détail, douleur par douleur

**1. Le document n'entre pas tout seul dans le dossier — 2/5** ●●●
> L'ANS ne prévoit l'intégration sans geste que si l'INS est qualifiée des deux côtés. Son objectif est
> un compte rendu « intégrable en 1 clic ».
- **Ce que nous avons** :
  - le rattachement automatique au patient par l'INS du CDA, avec comparaison côte à côte et jamais
    de création (E009 F002) ;
  - la vue patient avec sa timeline (F004) ;
  - dans Weda, le dossier du patient s'affiche sous le message et s'ouvre en un clic (E019 F2,
    validée, en attente de mise en ligne) ;
  - « Importer dans Weda » est prêt côté messagerie (F4).
- **Ce qui reste** :
  - l'import réel côté Weda (F3 à F5) ;
  - le classement en 1 clic (task-360) et la biologie dans la bannette (task-359) : **en pause depuis
    le 2026-10-10** ;
  - tant que Weda ne reçoit rien, le médecin enregistre à la main ;
  - pas de DMP.
- **Pour monter** : F1 (§ 4) amène à 4 ; F2 (DMP) amène à 5.

**2. Biologie : non reçue, illisible, en double, en retard, valeurs perdues — 4/5** ●●●
> Un lecteur d'Egora (01/2026) : « La MSS est mauvaise, la réception des examens et tout simplement
> foutoireuse. »
- **Ce que nous avons** :
  - le CDA N3 rendu ; le HPRIM converti en document de biologie, avec ses valeurs
    (task-389 à task-392) ;
  - les anomalies posées par le labo, le filtre « anormaux », les tendances sur 3, 6 et 12 mois ;
  - l'**acquittement en cinq actions**, tracé et partagé dans la boîte, et la tuile « à acquitter » ;
  - les doublons HPRIM détectés ; le CDA retenu en priorité dans un même envoi ;
  - une impression lisible.
- **Ce qui reste** :
  - le même résultat reçu en HPRIM par Apicrypt et en CDA par MSSanté donne **deux séries** (F3) ;
  - l'acquittement n'a ni échéance ni file de suivi (A4) ;
  - la biologie vers la bannette Weda est en pause (task-359) ;
  - la non-réception et les retards viennent du labo ou de l'opérateur : hors de notre portée.
- **Pour monter** : F3 et A4 amènent à 5.

**3. Trop de messageries, et des doublons entre elles — 2/5** ●●●
> Un généraliste : « apicrypt, MS santé, […] on s'y perd et bcp de doublon ». Ce qu'il demande, c'est
> un **agrégateur**, pas un opérateur de plus *(inférence)*.
- **Ce que nous avons** :
  - toutes les BAL MSSanté du praticien sous une seule connexion PSC (E016) ;
  - les doublons et « annule et remplace » signalés à l'intérieur de MSSanté ;
  - la messagerie embarquée dans Weda : un point d'entrée en moins.
- **Ce qui reste** : Apicrypt et les messageries régionales restent hors de notre boîte. Le médecin
  garde au moins deux boîtes.
- **Pour monter** : il faut décider F4 (agrégation Apicrypt). Sans elle, le plafond est 3.

**4. Trouver le bon destinataire — 3/5** ●●●
> 45 % d'adresses inactives, plusieurs adresses par praticien, comptes rendus qui arrivent « sur la
> mauvaise BAL ».
- **Ce que nous avons** :
  - l'Annuaire Santé (FHIR ou LDAP) sur 5 axes, avec toutes les adresses MSS du praticien ;
  - « possède une MSS » coché par défaut, et « recherche incomplète » signalée ;
  - un carnet alimenté par les échanges, avec favoris et groupes ;
  - une autocomplétion qui affiche la spécialité.
- **Ce qui reste** :
  - rien ne dit **quelle adresse fonctionne** : aucune mémoire des échecs (D2) ;
  - les avis de non-remise ne sont **ni demandés ni lus** : ils arrivent comme des mails ordinaires
    (D1) ;
  - la BAL préférentielle n'arrivera qu'en 2027.
- **Pour monter** : D1 et D2 amènent à 4 ; la BAL préférentielle de l'API FHIR amène à 5.

**5. Le canal sert à recevoir, presque jamais à échanger — 2/5** ●●●
> Les confrères n'écrivent pas par là ; l'urgence passe par le téléphone.
- **Ce que nous avons** :
  - répondre, et transférer avec les pièces jointes et l'archive XDM ;
  - le mode conversation ;
  - le chat IA, qui prépare « contacter un confrère » ;
  - les modèles et signatures (web) ;
  - l'accusé de lecture.
- **Ce qui reste** :
  - rien ne rend l'échange plus léger qu'un coup de fil : pas de réponses courtes sur mobile (D4) ;
  - pas de relance (A3), pas de message de dialogue (D5), pas de notification push (G1) ;
  - cette douleur dépend aussi de l'adoption par les confrères, qu'un client seul ne crée pas.
- **Pour monter** : G1, D4 et A3 amènent à 3.

**6. Pas de boîte de cabinet, pas de délégation à la secrétaire — 5/5** ●●●
> Irritants ANS n° 1 et n° 2 en 2023.
- **Ce que nous avons** :
  - la **secrétaire passe en un clic de sa boîte à celle d'un médecin** : plusieurs boîtes sur une
    seule connexion PSC, bascule par l'avatar (E016) ;
  - « Mes boîtes » vient de l'Annuaire et ouvre trois rôles : titulaire, **membre d'une BAL
    organisationnelle** (y compris la BAL de cabinet), délégataire (E020 F001) ;
  - **une base par boîte** : patients, étiquettes, acquittements, contacts et modèles partagés ;
    réglages et signatures personnels (F003) ;
  - l'envoi « pour le compte de la boîte » (F006) ;
  - **chaque acte imputé à son auteur réel** et un journal de la boîte (F004) ;
  - l'accès revalidé auprès de l'opérateur toutes les 5 minutes (F002).
- **Points ouverts** :
  - E020 attend sa recette ;
  - ouvrir un message ou envoyer prend environ 2 fois plus de temps dès 5 personnes (la correction,
    task-411, a été abandonnée) ;
  - l'AIPD est à compléter ;
  - dater ou borner une délégation relève de l'opérateur.
- **La douleur suivante** : maintenant que plusieurs personnes ouvrent la même boîte, il faut
  **travailler à plusieurs dedans** : affecter un message, file de tri, commentaires internes,
  collision. Ce n'est plus une question d'accès, mais de flux de travail (douleur 7, § 4 C).

**7. Volume, saturation, peur médico-légale de rater — 2/5** ●●
> 6 h 36 par semaine de courrier, comptes rendus et rendez-vous (thèse Prunières). « Une cinquantaine
> de mails par jour, au moins une heure. »
- **Ce que nous avons** :
  - un tableau de bord : résumé IA des non-lus du jour, biologie anormale, patients avec non-lus ;
  - des étiquettes IA de priorité (Très urgent, Urgent, Important) ;
  - des notifications bureau réglables (urgents seuls, biologie anormale) ;
  - les actions en masse, les conversations, la pastille d'intégration ;
  - **pour la biologie, la peur de rater est traitée** (acquittement, tuile « à acquitter ») : sur ce
    seul périmètre, le score serait 4.
- **Ce qui reste** :
  - hors biologie, rien ne dit qu'un message est **pris en charge** : pas de « Traité » (A1), pas de
    report (A2) ;
  - pas de vues par nature ni de regroupements (B1, B2), pas de règles de tri ;
  - les vues d'étiquettes IA ne gardent que les **non lus** : un message urgent lu en sort, même
    s'il n'a pas été pris en charge ;
  - pas de notification push (G1), pas de délégation du tri (C1, C2) ;
  - en résumé, **l'IA aide à voir l'important ; rien n'aide à vider la boîte**.
- **Pour monter** : A1, A2 et B1 amènent à 4 ; C1 et C2 amènent à 5.

**8. Messagerie patient : besoin réel, crainte d'être submergé — 2/5** ●●●
> 75 % ne l'ont jamais utilisée. 58 % des généralistes échangent déjà avec leurs patients hors
> consultation.
- **Ce que nous avons** :
  - à la réception, le message patient est distingué et le nom de l'usager affiché ;
  - à l'envoi : le garde-fou INS, l'opposition contrôlée côté serveur, « bloquer la réponse du
    patient » (`FIN`), le paquet XDM.
- **Ce qui reste** :
  - F007 n'est fait qu'à environ 10 % : mineurs, non-distribution, 25 Mo, MDN ;
  - pas de tri des réponses patients (E3) ;
  - pas de message « résultat normal » (E2).
- **Pour monter** : E1 amène à 3 ou 4 ; E2 et E3 amènent à 5.

**9. Ergonomie : sortir de son logiciel, clics, « moche » — 4/5** ●●
> « mal faites, non abordables, moches ».
- **Ce que nous avons** :
  - la messagerie **embarquée dans Weda sans nouvelle connexion** (E019 F1, validée, en attente de
    mise en ligne) ;
  - la lecture « contenu d'abord » ;
  - l'aperçu des pièces jointes et le téléchargement groupé en ZIP ;
  - le design system mobile Stitch ;
  - la recherche refondue (E022, E023) ;
  - des messages d'erreur en langage praticien ;
  - le travail sans carte.
- **Ce qui reste** :
  - enregistrer une pièce jointe dans le dossier demande encore des clics, tant que F4 n'est pas fait
    côté Weda ;
  - le mobile est en retrait : modèles, impression, annule et remplace ;
  - la taille du texte n'est pas réglable (G4).
- **Pour monter** : F1 et G2 amènent à 5.

**10. Impossible d'écrire hors MSSanté — 1/5** ●●
> D'où WhatsApp, Gmail, Doctolib et Omnidoc.
- **Ce que nous avons** : rien. L'espace de confiance l'interdit ; seul le patient est joignable, par
  Mon espace santé (douleur 8).
- **Pour monter** : D6 (lien sécurisé), à instruire avec le DPO et l'ANS. Le plafond est
  probablement bas.

**11. Lettres de sortie en retard ou absentes — 1/5** ●●
> « Une fois sur deux » selon la MACSF.
- C'est l'émetteur qui est en retard : un client ne peut pas montrer un document qu'il ne reçoit pas.
- **Leviers possibles** :
  - une relance « compte rendu attendu » (A3 étendu) ;
  - un jour, une alerte « patient sorti sans courrier », si nous recevions les notifications
    d'entrée et de sortie.
- La douleur reste largement hors de notre portée.

**12. Paramédicaux absents de la MSSanté — 2/5** ●●
> Les infirmiers utilisent Doctolib Discussion, Healico, Spico : instantané, mobile, photos de plaies.
- **Ce que nous avons** :
  - un annuaire qui couvre toutes les professions ;
  - l'envoi d'une photo prise avec l'appareil, sur mobile ;
  - un infirmier qui a une BAL peut se connecter.
- **Ce qui reste** :
  - pas d'instantané, pas de notification push ;
  - le stockage des photos hors de la galerie est à vérifier (G5) ;
  - le produit est pensé pour le médecin.
- **Pour monter** : G1 et D5 amènent à 3.

### Ce qu'il nous faudrait mesurer nous-mêmes Aucune source publique ne dit combien de documents un
généraliste reçoit par jour, ni la part MSSanté / Apicrypt / papier. Notre base de test réelle
(6 171 mails, boîte de Virginie) et nos traces peuvent le dire : c'est le **point de départ** de la
règle « mesurer avant d'améliorer » (voir § 6, manque M1).

---

## 3. Où nous sommes déjà devant

Ce qu'il ne faut **pas** reconstruire, et qu'il faut **mettre en avant** :

### Vue centrée patient

| Atout | Concurrence |
|---|---|
| **Vue patient** : tous les documents reçus pour ce patient, sur une timeline filtrable par catégorie (biologie, imagerie, consultation, **prescription**, hospitalisation…) | Les webmails MSSanté (Mailiz, Medimail, Apicrypt) restent organisés **par message**. Ranger par patient ne se fait que dans un logiciel métier (Doctolib) ou côté hôpital (Lifen), jamais dans un client de messagerie |
| **Historique des valeurs de biologie** sur une timeline : tendances, 11 catégories, plages de 3, 6 et 12 mois ; **synthèse clinique** de type IPS | Exigé par Ségur vague 2 pour les logiciels de cabinet (comparaison des résultats, LGC.MDV.08-09) ; absent des clients de messagerie |
| **Rattachement automatique** par l'INS ; comparaison côte à côte en cas de doute ; jamais de création ni de modification d'identité | Même modèle que les meilleurs (Epikur pour KIM, Lifen) |

### Classification automatique

| Atout | Concurrence |
|---|---|
| **À chaque message reçu**, la messagerie extrait l'INS, les traits d'identité, l'auteur, la date de l'acte, le code LOINC et la **catégorie clinique** (14 types). Elle rattache le document au patient, présente la paire CDA + PDF sur une seule ligne et convertit le HPRIM en biologie structurée | Doctolib classe par OCR dans son logiciel ; Lifen classe par IA côté hôpital ; Docman le fait au Royaume-Uni. **Aucun webmail MSSanté ne le fait** |
| **Étiquetage IA de la priorité** (Très urgent, Urgent, Important), avec reprise sur échec | Aucun client MSSanté ; Outlook « Prioritize », Superhuman côté grand public |
| **Doublons et « annule et remplace »** détectés et visibles (algorithme INT.18), navigation entre versions | Irritant officiel ; rarement traité côté client |

### IA au service du praticien

| Atout | Concurrence |
|---|---|
| **Synthèse IA** d'un message (patient, praticien, résumé clinique) ; **résumé des non-lus du jour** sur le tableau de bord | **Aucun client MSSanté ne propose publiquement d'IA sur les messages reçus.** Lifen et Doctolib ont de l'IA documentaire, mais dans le logiciel métier ou côté hôpital |
| **Chat conversationnel** sur plusieurs messages, **qui cite ses sources**, et qui **prépare des actions** : rédiger, répondre, **appeler le patient**, **envoyer un SMS au patient**, contacter un confrère. L'action est préparée, le praticien la déclenche | **Aucun équivalent trouvé**, ni en France ni dans les messageries étrangères étudiées. L'IA d'Epic (« Art ») s'arrête aux brouillons de réponse |
| **Modèles générés par l'IA** avec détection des variables (`{{SenderRPPS}}`…), **amélioration d'un texte** | Rédaction assistée chez Doctolib (logiciel métier) ; Superhuman et Nextcloud côté grand public. Rien côté client MSSanté |
| **Correcteur orthographique IA** avec aperçu des corrections (flag `ai_text_correction`, désactivé en production à ce jour) | Rien côté client MSSanté |
| **Fournisseur d'IA choisi par traitement**, LLM local possible (E017) ; l'IA est désactivable par l'établissement | Rare : seul Nextcloud fait tourner son classifieur en local |

### Recherche

| Atout | Concurrence |
|---|---|
| **Recherche plein texte fiable** sur tout l'historique : sans accents, casse ni ponctuation, dans l'objet, le corps, les documents et le nom des pièces jointes (E022) | Au niveau d'Outlook, au-dessus des webmails MSSanté |
| **Recherche sémantique** : trouver par le sens et non par le mot exact (par exemple « problème rénal » pour un compte rendu qui parle d'« insuffisance rénale »), dans une section à part (E022 F003, en attente de validation) | **Aucun client MSSanté** ; côté grand public, Gemini dans Gmail et Nextcloud |
| **Critères médicaux** : patient choisi dans une liste, biologie anormale, date du document, expéditeur (E023, en cours) | Propre au domaine |

### Biologie

| Atout | Concurrence |
|---|---|
| Biologie structurée (CDA N3 et HPRIM), anomalies posées par le labo, filtre « anormaux », **acquittement en cinq actions, tracé et partagé** dans la boîte | Exigé par Ségur vague 2 pour les logiciels de cabinet ; rare dans un client de messagerie |

### Traçabilité avancée et délégation

| Atout | Concurrence |
|---|---|
| **Chaque acte imputé à son auteur réel** : lecture, envoi, suppression, déplacement, étiquette, rattachement patient, acquittement, réglage. La trace porte le RPPS et le nom PSC, le rôle, la boîte, l'instant, l'action et l'objet. Les actes sans personne sont marqués **actes système** | Personne ne documente une imputation acte par acte, visible de toute l'équipe de la boîte |
| **Journal de la boîte** consultable par toute personne rattachée, filtrable par personne ; **journal d'audit PGSSI-S** conservé 10 ans, filtrable, avec export CSV complet ; impression avec pied de page de traçabilité | Mailiz notifie seulement le délégant par mail |
| **Délégation** : la **secrétaire bascule en un clic** de sa boîte à celle d'un médecin ; rôles titulaire, membre ou délégataire, décidés par l'Annuaire Santé ; BAL de cabinet ; **une base par boîte**, donc aucune copie de données de santé chez le délégataire ; envoi « pour le compte de » la boîte | Mailiz (délégation depuis la v1.6 du référentiel opérateurs), proxies Cerner, Team Inbox de Doctolib Connect (hors MSSanté) |
| **Accès revalidé auprès de l'opérateur toutes les 5 minutes** : une révocation ferme tout accès sans attendre | Non documenté ailleurs |

### Autres atouts

| Atout | Concurrence |
|---|---|
| **Travail sans carte** : lire, classer, rédiger ; les messages attendent ensuite un envoi confirmé avec la carte | Original |

**Conséquence** *(inférence)* : notre différenciation tient au **document compris et rangé par
patient**, et à une **IA qui agit** (chat avec actions, classification, recherche par le sens), sous
une **traçabilité complète**. Ces atouts vivent aujourd'hui surtout dans le **volet de lecture**,
la **vue patient** et le **chat**. Le prochain pas consiste à les remonter dans la **liste** et dans
le **flux de travail** (§ 4 A et B) : résumé clinique sur chaque ligne, priorité expliquée, tâches
proposées par le chat.

---

## 4. Les manques, domaine par domaine

Chaque ligne indique le manque, la preuve qu'il compte, qui le fait ailleurs, notre statut, et un
effort très approximatif (S < 1 semaine-task, M = 1 à 3 tasks, L = une EPIC) *(inférence)*.
Toute nouvelle action (traiter, affecter, commenter, reporter) relève de la **règle 14** : elle est
imputée à son auteur réel et tracée.

### A. La boîte comme file de travail (le cœur du sujet)

| Manque | Preuve | Ailleurs | Statut |
|---|---|---|---|
| **A1. Statut « Traité »** séparé de « lu » et d'« archivé » : un geste par message, horodaté et imputé ; compteur « reste à traiter » au lieu de « non lus » | Whittaker 1996, Grevet 2014 : la surcharge porte sur le **statut** ●●● | Inbox by Gmail « Done », Missive « Close » ≠ « Archive », Help Scout Active/Pending/Closed, Best Practice « Mark result as given » | Absent hors biologie |
| **A2. « À revoir le… »** : le message disparaît puis revient en tête à la date choisie (« contrôler l'INR dans 3 jours ») | 16 % des utilisateurs diffèrent au moins un mail par jour ; contournement par « non lu » (Sarrafzadeh ●●●) | HEY Bubble Up, Nextcloud, Superhuman | Absent |
| **A3. « En attente de réponse »** : un envoi qui attend une réponse revient au bout de N jours (« avis demandé au cardiologue, rien depuis 10 j ») | La boucle de coordination non fermée est un risque ; message de dialogue norvégien avec délai attendu de 3 à 5 jours ●●● | Superhuman Remind Me, Gmail Nudges, Nextcloud follow-up, Lifen (renvoi automatique) | Absent |
| **A4. Résultat → décision → tâche** : rien à faire / revoir non urgent / revoir urgent ; la tâche reste dans une file filtrable jusqu'à « communiqué au patient » | Best Practice Omni, HotDoc, Zedmed ●●● | Australie | Partiel : nos 5 actions d'acquittement couvrent la décision, pas l'**échéance** ni la **file de suivi** |
| **A5. Actions rapides composées** : « Intégrer + classer + traité » en un clic, enchaînement automatique sur le message suivant | QuickActions et AutoAdvance d'Epic ; Quick Steps de Docman (2 à 3 clics de moins par document) ●● | Epic, Docman, Nextcloud | Absent |
| **A6. Mise à zéro à l'arrivée** : tout ce qui date de plus de N jours passe « traité », réversible | Adoption : un médecin arrive avec des milliers de non lus *(inférence)* | Superhuman « Get Me To Zero » | Absent |

### B. Voir moins, voir mieux (segmentation et densité)

| Manque | Preuve | Ailleurs | Statut |
|---|---|---|---|
| **B1. Vues par nature clinique**, par défaut : Biologie · Courriers et comptes rendus · Patients (MES) · Pour info et notifications. Le flux principal ne garde que ce qui demande le médecin | Messages des machines = facteur de burnout (Tai-Seale ●●●) ; copies = 13 % du volume, −40 % en coupant le partage automatique ●● | HEY Imbox/Feed/Paper Trail, onglets Gmail, Apple Mail, Superhuman Split Inbox | Partiel : facettes de recherche (14 types), étiquettes ; **pas de vues de boîte** |
| **B2. Regroupement** : « 12 résultats normaux — Labo X » sur une ligne, « tout marquer traité » sauf ce qui est épinglé ou anormal | Inbox by Gmail Bundles/Sweep ●● | HEY Bundles, Shortwave | Absent |
| **B3. Ligne de résumé clinique dans la liste** : patient · type · **anomalie** (« Mme D. — NFS — Hb 8,1 ↓ »), calculée en tâche de fond et **sans LLM** quand le document est structuré | Nextcloud prévient : un LLM local est trop lent pour un résumé à la volée ●● | Superhuman Auto Summarize, cartes Gmail | Partiel : puces dans l'en-tête de lecture (weda2), pas dans la liste |
| **B4. Priorité expliquée** : une flèche plus une phrase « pourquoi ». Le niveau le plus haut repose sur des **règles déterministes** (anomalie labo, valeur critique, mention « urgent » d'un confrère), jamais sur le seul ML | Copilot « Prioritize » ●● ; mésaventure d'Apple Intelligence et de l'hameçonnage ●● | Microsoft | **Fait** : le motif de l'IA s'affiche en bandeau sur la ligne (`urgencyExplanation`) |
| **B5. Vue par patient depuis la liste** : grouper la boîte par patient (« 4 documents pour M. L. aujourd'hui ») | Le médecin pense par patient, pas par fil *(inférence)* ; HEY Collections | — | Partiel : vue patient, mais pas de regroupement dans la boîte |
| **B6. Bibliothèque des pièces jointes** : retrouver le dernier compte rendu ou PDF sans rouvrir les fils | HEY « All Files » | HEY | Partiel : timeline patient ; rien de transversal |

### C. Travailler à plusieurs (secrétariat, cabinet, remplaçant)

L'**accès partagé est fait** (douleur 6 = 5/5) : la secrétaire bascule en un clic de sa boîte à
celle d'un médecin ; BAL de cabinet, une base par boîte, chaque acte imputé (E016, E020). Ce qui
manque, c'est **le travail à plusieurs à l'intérieur** de la boîte partagée. Le socle E020 est
exactement ce qu'il faut sous ces fonctions.

| Manque | Preuve | Ailleurs | Statut |
|---|---|---|---|
| **C1. Affecter un message** à un praticien ou au secrétariat, avec une vue « pour moi » | Michigan −16 %, doublons −62 % ●● ; tri administratif britannique −80 % de courrier chez le médecin ●● | Front, Missive, pools Epic et Cerner | **Absent (F012 = 0 %)** |
| **C2. File « à trier » du secrétariat** : rattacher, classer, intégrer, et ne remonter au médecin que ce que le protocole exige. **Échantillon d'audit** hebdomadaire et registre des erreurs de routage | Medical Protection : garde-fous, « dans le doute, au médecin », la responsabilité reste au médecin ●●● | Docman, Workflow Optimisation (NHS) | Absent ; profil secrétaire « partiel » depuis avril |
| **C3. Commentaires internes** sur un message, jamais envoyés à l'expéditeur et imputés | Front, Spark, Missive ●●● | — | Absent (note d'acquittement biologie seulement) |
| **C4. Détection de collision** : « Cyril rédige une réponse », envoi bloqué si le fil a changé | Help Scout bloque l'envoi ●●● ; évite deux réponses contradictoires à un patient | Front, Help Scout | Absent |
| **C5. Rôles explicites** médecin / secrétaire / coordinateur, et ce que chacun peut faire | F010 « Must » NOVA non couvert | Elation : le personnel ne valide que par délégation explicite | Absent (F010 = 0 %) |
| **C6. Absence et remplacement** : réponse d'absence **qui nomme un remplaçant** (une personne, pas un groupe) ; délégation **datée** et **bornée** (« résultats seulement ») ; titulaire notifié | eHealthBox, Epic « Out of contact », proxies Cerner ●●● ; RFC 3834 au référentiel 1.7 | — | Réponse d'absence : absente. La délégation elle-même est livrée (E020) ; la dater ou la borner relève de l'opérateur |

### D. Envoyer et boucler

| Manque | Preuve | Ailleurs | Statut |
|---|---|---|---|
| **D1. Suivi d'acheminement lisible** : envoyé → délivré → lu → répondu, et **échec expliqué en français** (« adresse inexistante », « boîte pleine ») avec la marche à suivre | Référentiel 1.7 : DSN et NDR en français ●●● ; Lifen | Lifen, eHealthBox | Partiel : seuls la **demande** d'accusé de lecture et l'envoi de notre propre accusé existent. Constaté dans le code le 2026-11-11 : **aucune demande DSN** (`NOTIFY`, `ENVID`) et **aucun rapport entrant lu** ; un avis de non-remise arrive comme un mail ordinaire. Le « MDN / DSN OK » d'E009 est faux |
| **D2. Fiabilité des adresses** : signaler dans l'autocomplétion une adresse qui a **déjà échoué**, et préférer la BAL préférentielle quand l'API FHIR la publiera (2027) | 45 % d'adresses inactives ●●● ; attribut `rank` annoncé par l'ANS | — | Absent |
| **D3. Envoi programmé** (« envoyer lundi 8 h ») | Confort ; envois hors heures *(inférence)* | Gmail, Outlook | Absent |
| **D4. Blocs de texte et réponses courtes** (« Bien reçu, je vois le patient le… »), partagés dans le cabinet, insérés par un raccourci | Smart Reply ≈ 10 % des réponses mobiles ●●● ; Nextcloud Text blocks | Nextcloud, Superhuman | Partiel : modèles sur le web, **absents du mobile** |
| **D5. Message de dialogue entre confrères** : court, rattaché à un patient, délai de réponse attendu affiché, « non urgent » explicite | Norvège « dialogmelding » ●●● ; le canal ne sert pas à échanger aujourd'hui (§ 2.5) | Norvège | Absent *(pari)* |
| **D6. Écrire à un non-MSSanté** : lien sécurisé à durée limitée | HIN Mail Global (30 jours), NHSmail `[secure]` ●● ; contournements WhatsApp et Gmail ●● | Suisse, Royaume-Uni | Absent — **à instruire réglementairement** (hors espace de confiance) |

### E. Patient (Mon espace santé)

| Manque | Preuve | Statut |
|---|---|---|
| **E1. Terminer F007** : mineurs, retours de non-distribution, 25 Mo, réponse de l'usager, MDN RFC 8098 | Cadre protecteur (le médecin initie et clôt) ; 33,6 % d'activation de MES | ≈ 10 % |
| **E2. Message « résultat normal » au patient** quand tous les résultats d'une date sont « rien à faire » | HotDoc ●●● ; évite les appels « alors, mes résultats ? » | Absent |
| **E3. Tri des réponses patients** (administratif → secrétariat, clinique → médecin) | Classifieur administratif/clinique à ≈ 89 % (Johns Hopkins ●●) ; Emory −30 % chez le clinicien ●● | Absent |

### F. Intégration et parcours

| Manque | Preuve | Statut |
|---|---|---|
| **F1. Finir E019 côté Weda** : ouverture d'office (F3), « Importer dans Weda » (F4), envoi depuis le dossier (F5) ; **reprendre 358-361** (compteur dans l'en-tête, biologie dans la bannette, classement en 1 clic, « Envoyer par MSSanté ») | KBV/kv.dox, eHealthBox « un seul client », séminaire DNS « 1 clic » ●●● | Côté messagerie livré ; **côté Weda en pause** |
| **F2. Dépôt DMP** du document émis | Obligation Ségur ; amende censurée en 2025 mais pression maintenue | Absent (côté LGC probablement *(inférence)*) |
| **F3. Une biologie, un résultat**, tous canaux confondus : rapprocher HPRIM (Apicrypt) et CDA (MSSanté) d'un même examen | Doublons entre messageries ●●● ; palier 2 (3 formats) | HPRIM×HPRIM détecté (task-391) ; HPRIM/CDA → deux séries |
| **F4. Agrégation Apicrypt** dans la même boîte | « Une messagerie unique » demandée ●●● ; Doctolib importe MSSanté et Apicrypt | Absent — **décision stratégique** |

### G. Mobile

| Manque | Preuve | Statut |
|---|---|---|
| **G1. Push** : critique seulement par défaut ; digest à heures choisies ; réglable par flux | Kushlev 2016, Mark 2016 ●●● | **Absent** |
| **G2. Parité** : modèles, annule et remplace, bannière doublon, impression ou partage PDF, journal | E012 §9 | Absent sur mobile |
| **G3. Balayages limités à deux actions constantes** (Traité, Plus tard), annulation visible, équivalent accessible (TalkBack et VoiceOver) | NN/g, ticket Thunderbird Android ●●● | Balayages présents ; à re-cadrer sur A1 et A2 |
| **G4. Lisibilité réglable** : taille de texte, cibles ≥ 44 dp, vue compacte ou cartes | Revue 2025 sur les seniors ●● ; médecins de plus de 60 ans moins équipés (DREES) | Partiel (Stitch : cibles 44 px) |
| **G5. Photo dans un coffre, jamais dans la galerie** | Siilo ●● | Probablement conforme (`saveToGallery` absent du code) — à vérifier |

### H. IA : ce qui vaut la peine

Nous sommes devant. Ce qui manque, c'est de **la faire travailler pour le tri**, sans lui confier la
décision :
- résumé d'une ligne **dans la liste** (B3) ;
- priorité **expliquée** (B4) ;
- **extraction de tâches** (« revoir le patient », « rappeler le labo ») proposée, jamais créée
  d'office (Gmail AI Inbox) ;
- **classement suggéré** à valider : type de document, destination dans le dossier (athenahealth,
  Docman ; nos 14 types médicaux existent déjà) ;
- **routage suggéré** au secrétariat pour l'administratif (E3).

**Attentes réalistes** pour les brouillons de réponse :
- usage d'environ 20 % ; −14 points de charge ressentie, **temps inchangé** (Garcia, Stanford) ;
- gain de temps surtout pour le **secrétariat** ;
- mesurer la charge perçue, pas seulement les secondes.

### I. Mesurer la charge

| Manque | Preuve | Statut |
|---|---|---|
| **I1. Tableau de charge par boîte** : messages par jour et par nature, part traitée par le secrétariat, délai de traitement, **travail hors heures** | Sinsky/Shanafelt : « mesurer, réduire, déléguer » ; le temps hors heures prédit le burnout (Akbar, Arndt ●●●) | Absent (task-452 mesure seulement la recherche) |

---

## 5. Principes UX proposés

Une charte courte, à faire valider avant d'écrire les maquettes Stitch :

1. **Traité, pas lu.** Le compteur qui compte est « reste à traiter ».
2. **Un patient, pas un fil.** Patient, type et anomalie sont visibles dans la liste.
3. **Rien de rouge sans raison.** Toute priorité dit pourquoi ; le niveau critique vient de règles
   déterministes.
4. **Le médecin ne voit que ce qui demande le médecin.** Le reste va au secrétariat ou dans « Pour
   info », sans jamais disparaître.
5. **Un geste par message.** Annulation visible plutôt que confirmation ; un geste n'a qu'un seul
   sens dans toute l'application.
6. **Silencieux par défaut.** Les notifications sont réservées au critique ; le reste est regroupé à
   heure fixe.
7. **Rien ne reste en suspens.** Tout envoi qui attend une réponse revient, et tout report revient.
8. **L'IA propose, l'humain dispose.** Elle cite ses sources et n'envoie ni ne classe rien d'office.

**Ce que nous ne recommandons pas** :
- pixels de suivi ;
- brouillons IA envoyés sans relecture ;
- chat sur email par défaut (Delta Chat) : réserver une vue « conversation » optionnelle ;
- mise à zéro irréversible ;
- priorité ML opaque au niveau critique.

---

## 6. Feuille de route proposée

**Horizon 1 — rendre la boîte vidable**, effort modéré et effet immédiat :
- **A1 Traité**, **A2 À revoir le…**, **B1 vues par nature** (B4, la priorité expliquée, est déjà
  là).
- **G1 push mobile sobre**.
- **C6 réponse d'absence avec remplaçant** (à vérifier : Sieve exposé par l'opérateur Mailiz).
- **I1 mesure de charge**, posée **avant** les changements, pour juger les suivants (règle d'or 5).
- Débloquer **F1** : la partie Weda d'E019 et les tasks 358-361. C'est la douleur n° 1, et le code
  messagerie est prêt.

**Horizon 2 — déléguer et boucler** :
- **C1-C5 secrétariat** : affecter, file de tri, commentaires internes, collision, rôles.
- **A4 biologie → tâche**, **B2 regroupements**, **B3 ligne clinique**.
- **D1-D2 suivi des envois et fiabilité des adresses** : référentiel 1.7, NDR en français.
- **A3 en attente de réponse**, **A5 actions composées**.
- **G2 parité mobile**, **D4 blocs de texte**.

**Horizon 3 — paris structurants** :
- **E1-E3 Mon espace santé complet**.
- **F3/F4 une biologie par résultat, agrégation Apicrypt** : à décider.
- **D5 message de dialogue**, **D6 envoi hors MSSanté** (instruction réglementaire).
- **F2 DMP**.
- **H extraction de tâches** et routage suggéré.

---

## 7. Calendrier réglementaire à anticiper

| Échéance | Ce qui change | Impact pour nous |
|---|---|---|
| **Fin 2026 – janvier 2027** | Mailiz : interfaces historiques retirées ; seule reste l'**API LPS** (IMAP XOAUTH2 avec jeton PSC) ; changement de serveur *(extrait, à confirmer avec l'ANS)* | Vérifier que notre connexion Mailiz n'utilise que l'API LPS |
| **2027** | **Référentiel opérateurs 1.7** opposable par arrêté : DSN et NDR en français, réponse automatique RFC 3834, transfert Sieve entre les BAL PER, antivirus des PJ, alertes de quota 80/90/100 % | D1, C6 ; nos jauges de quota sont déjà à 80/90 % |
| **Avril 2027 → avril 2028** | Annuaire : API FHIR MSSanté, BAL rattachée à une situation d'exercice, **BAL préférentielle**, fin des BAL « type 10 » | Choix du destinataire (D2), recherche annuaire (F008) |
| **Ségur vague 2, LGC** (échéance de mise à jour à vérifier : 2027 ou 2028) | Biologie CDA R2 N3 structurée, comparaison des résultats, détection des doublons | Nous y sommes déjà ; F3 complète |
| **Biologie, palier 2** | PDF + HPRIM + CDA dans le même envoi | Le CDA prioritaire est déjà géré (task-390) ; F3 pour les envois séparés |

---

## 8. Questions ouvertes pour la décision

1. **Agréger Apicrypt** (F4) : c'est la demande « messagerie unique ». Elle suppose un accès Apicrypt
   (API ou POP chiffré) et un dédoublonnage croisé.
2. **Où vit la « tâche »** (A4, H) : dans la messagerie, ou poussée dans Weda ? Il faut éviter deux
   listes de tâches.
3. **Le DMP** (F2) : par la messagerie ou par Weda ?
4. **Rôle « secrétaire »** (C5) : qui l'attribue ? L'annuaire (RPPS+) ou le titulaire de la boîte ?
5. **Lien sécurisé hors MSSanté** (D6) : hors espace de confiance, à instruire avec le DPO et l'ANS.

---

## 9. Sources principales

**Douleurs et besoins en France**
- Séminaire DNS/ANS/CNAM « Usages numériques en médecine de ville », 01/2024 : https://www.fncs.org/sites/default/files/Restitution_seminaire_Institutionnels_et_editeurs.pdf
- Comité opérateurs MSSanté « Sentinelle », 06/2023 : https://mssante.fr/documents/16106/0/MSS_comit%C3%A9_op%C3%A9rateurs_Sentinelle_4_20230608.pdf/436050bb-905e-4c5d-b34d-faedff42f61a
- Comité opérateurs, 06/2026 : https://mailiz.mssante.fr/documents/16106/0/CR_MSS_comit%C3%A9_op%C3%A9rateurs_NouveauDispositif_1_20260604_VF.pdf/7da270a5-58db-488d-a464-9e188e630b97
- Comité opérateurs, 07/2026 (45 % d'adresses inactives, référentiel 1.7) : https://mailiz.mssante.fr/documents/16106/0/MSS_comit%C3%A9_op%C3%A9rateurs_NouveauDispositif_3_20260702.pdf/334e3848-8194-4253-b281-69cf2eb85c18
- DREES, Études et Résultats n° 1139 (2020) : https://www.drees.solidarites-sante.gouv.fr/sites/default/files/er1139.pdf
- URPS Centre-Val de Loire 2024, via Egora 01/2026 : https://www.egora.fr/actus-pro/sante-numerique/sante-numerique-la-moitie-des-medecins-pensent-que-leur-pratique-sera
- Thèse Ajoodha, Lille 2023 : https://pepite-depot.univ-lille.fr/LIBRE/Th_Medecine/2023/2023ULILM006.pdf
- Corpus de 1 959 généralistes (thèse Lafortune 2022) : http://www.apima.org/img_bronner/These_monespacesante_Commentaires_libres_questionnaire1.pdf
- Thèse Prunières (temps non médical), Caducée 2018 : https://www.caducee.net/actualite-medicale/14131/
- URPS IDF (coût des outils), Caducée 2024 : https://www.caducee.net/actualite-medicale/16435/

**Marché français**
- Lifen : https://www.lifen.fr/en/care/lifen-documents · Doctolib : https://media.doctolib.com/image/upload/mkg/file/fiche_produit_doctolib_medecin_generaliste_web · Apicrypt 2024 : https://apicrypt.org/public/files/communication/CN_COM_Retrospective_APICRYPT_2024_.pdf
- Mailiz, page éditeurs (API LPS) : https://mailiz.mssante.fr/editeurs · Séminaire API LPS : https://industriels.esante.gouv.fr/sites/default/files/media/document/mss_seminaire_integration-api_lps_dans_lps-dui_20240119.pdf
- Référentiel #2 Clients : https://industriels.esante.gouv.fr/sites/default/files/media/document/ANS_MSS_Ref2_Clients_de_messageries_MSSant%C3%A9_v1.0_20230131.pdf
- Mon espace santé, spécification messagerie V1.3 : https://mssante.fr/documents/16106/0/ENS-Mon_espace_sante_-_Messagerie_V1.3.pdf/358418e6-9864-4876-be14-6fcf9e5c7ae3
- Ségur vague 2, couloir médecin de ville : https://esante.gouv.fr/segur-numerique-sante/vague-2/dispositif-lgc-couloir-medecin-ville

**International et littérature sur la boîte du médecin**
- Tai-Seale 2019 (Health Affairs) : https://www.sutterhealth.org/research/publications/md-wellbeing-in-basket-messages-from-ehr-algorithms
- Arndt 2017 : https://www.annfammed.org/content/15/5/419 · « More Tethered » 2024 : https://www.annfammed.org/content/22/1/12 · Murphy 2016 : https://pmc.ncbi.nlm.nih.gov/articles/PMC4860883 · Murphy 2019 : https://pmc.ncbi.nlm.nih.gov/articles/PMC6784746/ · Sinsky 2022 : https://pmc.ncbi.nlm.nih.gov/articles/PMC9640509/
- Garcia 2024 (brouillons IA) : https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2816494
- Michigan (routage) : https://www.medicaleconomics.com/view/two-simple-workflow-tools-cut-physician-message-load-by-16- · AMA STEPS Forward : https://www.ama-assn.org/practice-management/digital-health/managing-ehr-inbox-takes-system-here-s-how-set-one
- Tri du courrier au Royaume-Uni (Medical Protection) : https://www.medicalprotection.org/uk/articles/easing-the-growing-burden-in-general-practice
- Best Practice Omni (résultats) : https://kb.bpsoftware.net/bpomni/Clinical/Inbox.htm · HotDoc : https://support.hotdoc.com.au/hc/en-gb/articles/360040927531-Getting-Started-with-Results
- KBV kv.dox (pas de transfert vers le dossier) : https://kbv.de/media/sp/2023_Aug-Nov_FAQs_Webinare_kvdox.pdf · eHealthBox : https://ehealth.fgov.be/ehealthplatform/fr/service-ehealthbox.pdf
- Proxies Cerner : https://hi.northernlighthealth.org/Flyers/Non-Providers/Imaging/Message-Center-Proxies.aspx · Dialogmelding norvégien : https://kompetansebroen.no/wp-content/uploads/2024/08/Retningslinje-for-bruk-av-dialogmeldinger-utenom-innleggelser.pdf

**Ergonomie des clients mail**
- Whittaker & Sidner 1996 : https://www.chi1996.chistatic.hosting.acm.org/proceedings/papers/Whittaker/sw_txt.html · Sarrafzadeh 2019 : https://www.microsoft.com/en-us/research/publication/characterizing-and-predicting-email-deferral-behaviour/ · Mark 2016 : https://www.microsoft.com/en-us/research/wp-content/uploads/2016/06/Email20Duration20Camera20Ready20submission3-1.pdf · Kushlev 2016 : https://www.interruptions.net/literature/Kushlev-CHI16.pdf
- HEY : https://hey.com/features/ · Superhuman Split Inbox : https://help.superhuman.com/article/557-split-inbox-revised · Copilot Prioritize : https://support.microsoft.com/topic/prioritize-my-inbox-65e37040-2c90-4ee3-86d9-e95d5ba0e3cb
- Help Scout (collision) : https://docs.helpscout.com/article/99-traffic-cop · Missive (fermer ≠ archiver) : https://learn.missiveapp.com/missive-concepts-explained/what-is-the-difference-between-archiving-and-closing
- Nextcloud Mail : https://docs.nextcloud.com/server/32/user_manual/en/groupware/mail.html · NN/g, balayage contextuel : https://www.nngroup.com/articles/contextual-swipe/

**Limites de cette recherche**
- esante.gouv.fr bloque les lecteurs automatiques : certains chiffres ANS ne sont connus que par
  extraits de moteur.
- Les chiffres britanniques (−80 %, 45 min) viennent de promoteurs.
- Les études de boîte du DPI sont surtout avant/après sur un seul site.
- Aucune donnée publique sur le nombre de documents par généraliste et par jour.
