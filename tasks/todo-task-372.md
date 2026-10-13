# todo-task-372.md — L'import dans le dossier Weda classe chaque document chez le bon patient, et dit vrai sur ce qui a été importé ou envoyé

**Repos**: client-angular, api-mail
**Dependencies**: task-371 (le mail affiché est celui qui est sélectionné — sans elle, l'import reçoit le contenu du mail précédent)
**Epic**: E019
**Single frontend**: true — l'import Weda n'existe que dans weda2 embarqué.
**Priorité**: **1** — erreurs d'identito-vigilance : un document médical classé dans le dossier d'un autre patient, avec une présélection présentée comme fiable (trouvée par INS).

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-09, ANG-18 ✔ (volet import), ANG-47, ANG-48, ANG-49, ANG-63, ANG-64**).
> Décisions de l'intégration : mémoire `weda-nova-integration` (EPIC E019).

## Ce qui est établi

- **ANG-09** — `weda-import.component.ts:189-194, 258-287, 530-552` : rien ne lie une préparation d'import à l'ouverture qui l'a lancée. « Annuler » pendant la préparation puis ouverture sur B : la résolution tardive de A sélectionne le patient de A ; aucun bouton radio n'est coché, l'invite est masquée, « Importer » est actif.
- **ANG-48** — `weda-import.component.ts:540-551`, `weda-import.utils.ts:175-180` : un message portant les documents de deux patients présélectionne le premier trouvé par INS et coche tous les documents.
- **ANG-47** — `weda-import.component.ts:442-519` : le compte rendu d'un import (succès ou erreur) reste affiché sur le message suivant.
- **ANG-18 (import)** — `weda-import.component.ts:601-613` : deux pièces de même nom → la première est importée deux fois, la seconde jamais, « 2 document(s) importé(s) » affiché (`occurrence` jamais transmis, `mss-api.service.ts:1884-1895`).
- **ANG-49** — `mail-compose.component.ts:902-904, 1354-1364, 1714-1726, 1775-1788` : l'avis `document-sent` envoie tous les `fileStreamId` de l'intention, même ceux retirés ou écartés ; un envoi mis de côté (202) ou en file n'en envoie aucun. Weda écrit donc de fausses traces « Traces MSSanté », et en omet de vraies.
- **ANG-63** — « Envoyer » depuis le dossier Weda n'aboutit à rien, sans message, quand l'intégration est indisponible.
- **ANG-64** — import en échec ou hors délai : « Réessayez » crée des doublons (import Weda non transactionnel).

## Objective

Que l'import dans le dossier patient Weda **ne classe jamais un document chez le mauvais patient**, que la présélection d'un dossier ne soit faite que si elle est certaine, et que ce que weda2 dit à Weda et au médecin (documents importés, documents envoyés) corresponde exactement à ce qui s'est passé.

### Périmètre

1. **Préparation liée à son ouverture** : compteur de génération vérifié après chaque attente ; sélection remise à zéro si le patient choisi n'est plus listé ; « Annuler » indisponible pendant un import en cours.
2. **Présélection sûre** : un dossier n'est présélectionné que si **tous** les documents cochés se résolvent vers le même dossier ; sinon, choix explicite et seuls les documents du patient choisi cochés par défaut.
3. **Compte rendu rattaché au message** : succès et erreur effacés au changement de mail.
4. **Pièces homonymes** : le rang `occurrence` est transmis au téléchargement (le serveur le gère depuis AUD-41).
5. **Avis d'envoi exact** : `fileStreamIds` calculés sur les pièces réellement jointes au moment de l'envoi ; pas d'avis si aucune pièce de l'intention ne part.

> **⚠️ Arbitrage humain requis — envois différés.** Pour un envoi mis de côté (202, « à confirmer avec la
> carte ») ou mis en file hors ligne, la trace Weda doit-elle (a) être écrite plus tard, à l'envoi
> effectif (api-mail ou weda2 doit alors la déclencher), ou (b) ne pas l'être, en documentant la
> limite ? La forge ne tranche pas.
>
> **Décision humaine (2026-10-13) : (b) pas de trace pour un envoi différé, limite documentée.** weda2
> n'écrit la trace que pour un envoi immédiat réussi ; la limite est documentée dans E019 (et dans la
> `## Develop log`). Écrire la trace à l'envoi effectif reste un chantier à part (api-mail devrait prévenir
> Weda).

6. **Intégration indisponible** : quand weda2 est embarqué mais que l'intégration ne répond pas, un message clair indique de passer par l'ancien écran.
7. **Échec ou délai dépassé** : message « vérifiez le dossier patient avant de réessayer ». Côté Weda (hors forge) : transaction couvrant tout l'import, à signaler à l'équipe Weda.

## Definition of Done

- [ ] Build et tests weda2 verts ; api-mail vert
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] préparation de A abandonnée puis ouverture sur B : la résolution de A ne modifie ni la liste ni la sélection de B
  - [ ] deux documents de deux patients différents : aucune présélection, choix exigé
  - [ ] le compte rendu d'import de A n'est plus affiché sur B
  - [ ] deux pièces `scan.pdf` : deux téléchargements avec `occurrence` 0 et 1, deux contenus distincts envoyés à Weda
  - [ ] pièce de l'intention retirée avant l'envoi : son `fileStreamId` n'est pas dans l'avis ; aucune pièce de l'intention : pas d'avis
  - [ ] intégration indisponible : le message s'affiche
- [ ] Test d'intégration de bout en bout pour `GET …/download/attachment/{name}?occurrence=1` : la seconde pièce homonyme est renvoyée (octets lus dans la réponse réelle), vu rouge si le paramètre est ignoré (règle 1b) — à ajouter s'il n'existe pas déjà depuis AUD-41
- [ ] Scénario E2E-WEDA-002 versionné (v2) : import d'un message à deux documents de deux patients, sans présélection ; pièces homonymes importées toutes deux — angular `requis`, mobile `non-applicable` (l'import Weda n'existe pas sur mobile)
- [ ] Scénario E2E-WEDA-003 versionné (v2) : pièce de l'intention retirée → aucune trace d'envoi pour elle
- [ ] Trou du filet : ligne dans `conventions/e2e.md`
- [ ] INS ni affichée ni journalisée (inchangé)

## Manual Test Plan

1. Weda Échanges, mail portant les CDA de deux patients connus par INS : « Importer » → aucun dossier présélectionné ; choisir un patient → seuls ses documents sont cochés.
2. Ouvrir l'import de A, cliquer « Annuler » pendant « Préparation… », ouvrir l'import de B → la fenêtre de B n'a aucune sélection héritée de A.
3. Importer A, sélectionner B → aucun « document(s) importé(s) » affiché sous B.
4. Mail avec deux pièces `scan.pdf` différentes → les deux sont classées, chacune avec son contenu.
5. Depuis le dossier Weda, « Envoyer » un document, le retirer de la rédaction, joindre autre chose, envoyer → aucune trace « document envoyé » pour le document retiré.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — intégration DPI ↔ MSSanté (import des documents reçus dans le dossier)
- **Exigences DSR honorées** : identito-vigilance du rattachement d'un document reçu au dossier patient (RNIV : pas de rapprochement présenté comme certain sans concordance des traits)
- **INS** : récupérée depuis les documents (CDA) et utilisée pour la résolution côté Weda ; la présélection n'a lieu que si toutes les identités concordent ; INS jamais affichée ni journalisée par weda2
- **Authentification PS** : inchangée (session PSC / e-CPS du praticien)
- **Habilitations** : inchangées (droits Weda du praticien sur le dossier)
- **Interop CI-SIS** : CDA r2 et IHE XDM — lecture seule des documents reçus
- **Tracé PGSSI-S** : traces « Traces MSSanté » de Weda exactes (documents réellement envoyés) ; décision sur les envois différés (arbitrage ci-dessus)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé
