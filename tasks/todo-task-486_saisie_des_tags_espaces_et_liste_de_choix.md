# todo-task-486.md — Saisie des tags : espaces acceptés et liste de choix

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E024

**Priorité**: EPIC E024, demandée par l'humain le 2026-11-16, en réécrivant task-456 (les vues par nature deviennent
des vues par tag). Plus les tags servent à lire la boîte, plus leur saisie doit être rapide et sans refus
incompréhensible. Peut passer avant ou après task-456 : la liste de choix propose les tags qui existent.

> **Constat humain du 2026-11-16** : un tag qui contient un espace est refusé. Le refus vient du serveur :
> `MailController.cs:1805`, `if (request.TagName.Contains(' ')) throw new ValidationException("Tag name must not
> contain spaces.")`. Le nom est aussi plafonné à 20 caractères (`:1800`), alors que le tag système
> « Professionnel de santé » de task-456 en compte 22.

## Ce qui est établi

- `POST api/v1/Mail/folders/{foldername}/emails/{emailid}/tags` (`AddTagRequest.TagName`) pose un tag ; tracé
  `TagAdded` au nom de la personne.
- Le code d'un tag est `NormalizeTagCode(nom)` : majuscules, sans accents. Un tag de même code est réutilisé, jamais
  dupliqué.
- **Des codes avec espace existent déjà** : les tags IA « Très urgent » (code `TRES URGENT`) passent par
  `EmailTaggingService`, sans la validation du contrôleur. Les routes `tags/{tagcode}/…` les servent (le contrôleur
  décode le code avec `Uri.UnescapeDataString`).
- **Aucune route ne liste les tags de la boîte** : `GetTagFoldersAsync` ne rend que les tags qui ont un non lu.
- Saisie actuelle : un champ libre sans suggestion, dans weda2 (`mail-tag.component`, `data-testid="mail-tag-input"`)
  et sur mobile (`mail-detail.component`).
- Les tags appartiennent à la **boîte** (règle 14) : toutes les personnes de la boîte partagent la même liste.

## Objective

Poser un tag se fait en quelques touches : on tape le début d'un nom, la liste propose les tags de la boîte, on
choisit. Un nom de plusieurs mots est accepté.

Règles :
- **Espaces acceptés** : le nom est nettoyé (espaces de début et de fin retirés, espaces internes consécutifs réduits
  à un seul) et garde sa casse et ses accents à l'affichage. « Courrier urgent », «  courrier   URGENT  » et
  « Courrier Urgent » désignent le **même** tag (même code).
- **Longueur** : 40 caractères au plus après nettoyage. Refusés : un nom vide, un caractère de contrôle. Refus en
  `ProblemDetails` (400), avec un `detail` en français lisible par le praticien.
- **Liste de choix** à l'ouverture de la saisie :
  - elle propose **tous les tags de la boîte** : système, IA, utilisateur ;
  - elle se filtre à la frappe, sans tenir compte de la casse ni des accents ; les tags qui **commencent** par le
    texte saisi d'abord, puis ceux qui le **contiennent** ;
  - les tags déjà posés sur le message n'y figurent pas ;
  - clavier : flèches pour parcourir, Entrée pour choisir, Échap pour fermer ;
  - si aucun tag n'a exactement ce nom, la dernière ligne propose « Créer le tag « … » » ;
  - sur mobile, la même liste sous le champ, au toucher.
- **Liste des tags de la boîte** servie par le serveur (par exemple `GET api/v1/Mail/tags`), avec nom, code, type et
  couleur, triée : système, IA, utilisateur, puis alphabétique.

### Hors périmètre

- Renommer, recolorer ou supprimer un tag de la boîte.
- Les vues par tag, les tags système et la combinaison de tags : task-456.

## Definition of Done

- [ ] Validation du nom de tag : espaces acceptés, nettoyage, 40 caractères, caractères de contrôle refusés ;
      `detail` en français. Tests unitaires de la normalisation (espaces multiples, casse, accents → même code).
- [ ] Route de liste des tags de la boîte ; `TagDto` (dtos-mss) publié si le contrat change ; miroirs TypeScript.
- [ ] **Test d'intégration de bout en bout (règle 1b)** : poser « Courrier urgent » → 200, le tag est relu sur le
      message et dans la liste des tags ; poser «  courrier   URGENT  » sur un autre message → même tag, pas de
      doublon dans la liste ; un nom de 41 caractères → 400 en `ProblemDetails` ; la liste rend les tags système, IA
      et utilisateur dans l'ordre. Vu rouge (le refus actuel des espaces fait échouer le premier cas).
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : liste ouverte à la saisie, filtre sans
      casse ni accents, tags déjà posés exclus, Entrée choisit, « Créer le tag » quand aucun nom exact.
- [ ] **Scénario e2e**, mobile et angular requis, vu rouge :
      - `E2E-TAG-001` v1 : sur un message, taper « cour », choisir « Courrier urgent » dans la liste ; créer un tag
        « Avis cardio » avec un espace ; les deux tags apparaissent sur le message.
- [ ] `data-testid` sur la liste et ses lignes, conventions de libellés, aucune donnée de santé dans les libellés
      ni les logs.
- [ ] Build et tests verts (api-mail, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend et weda2 lancés sur la boîte de formation de Virginie.
2. Ouvrir un message, cliquer sur « + » des tags : la liste des tags de la boîte s'affiche.
3. Taper « urg » : « Urgent », « Très urgent » et les tags utilisateur qui contiennent « urg » ; Entrée pose le
   premier.
4. Taper « Avis cardio » : la dernière ligne propose « Créer le tag « Avis cardio » » ; le choisir : le tag est posé.
5. Sur un autre message, taper « avis CARDIO » : la liste propose « Avis cardio » existant, pas de doublon créé.
6. Mobile : même parcours depuis le détail d'un message.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — organisation du travail
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : titulaire, membre, délégataire, sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : `TagAdded` au nom de la personne, inchangé ; la lecture de la liste des tags n'est pas un accès
  à une donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : non applicable
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé
