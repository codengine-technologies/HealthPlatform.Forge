# todo-task-446.md — Recherche : lire un résultat (extrait surligné, patients trouvés)

**Repos**: client-angular, api-mail
**Dependencies**: done-task-444 (réponse enrichie), done-task-445 (mode résultats)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Le médecin doit reconnaître le bon message sans l'ouvrir,
et passer d'un nom tapé au dossier du patient en un geste.

> **Origine.** Analyse du 2026-11-10 (surlignage et « Personnes » d'Outlook). `api-mail` figure dans les Repos pour le
> catalogue e2e.

## Objective

Dans le mode « Résultats de recherche » de weda2, chaque résultat explique pourquoi il est là, et les patients désignés
par la recherche sont proposés en tête.

Règles :
- **Extrait surligné** : sous l'objet de chaque résultat, l'extrait rendu par le serveur, avec les termes trouvés
  surlignés.
- **Endroit trouvé** : une mention courte indique où le terme a été trouvé (« Objet », « Corps », « Document médical »,
  « Expéditeur », « Pièce jointe »), ou « Proche par le sens » pour un résultat proche.
- **Dossier d'origine** : chaque résultat porte le nom du dossier où il est rangé (« Boîte de réception »,
  « Archives »…).
- **Patients trouvés** : au-dessus des résultats, une rangée « Patients » montre au plus 5 patients désignés par la
  recherche (nom de naissance en majuscules, nom d'utilisation s'il diffère, prénom, date de naissance, sexe, nombre de
  messages, mention « INS qualifiée » le cas échéant). Un clic ouvre la vue existante « Mails du patient ».
  - L'INS n'est jamais affichée.
  - Aucun patient trouvé : la rangée n'est pas affichée.
- Le surlignage est aussi appliqué dans le message ouvert depuis les résultats (objet et corps).

### Hors périmètre

- Le mobile : task-451.
- Les patients proposés pendant la frappe : task-449.

## Definition of Done

- [ ] Build passes (0 errors) : weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `nx test weda2`, `nx test mss-lib`
- [ ] Tests de composant, chacun vu rouge par mutation : extrait surligné aux positions rendues (y compris un mot
      accentué tapé sans accent) ; mention de l'endroit trouvé ; dossier d'origine ; rangée Patients (affichée, masquée
      sans patient, clic vers « Mails du patient ») ; aucune INS dans le rendu ; surlignage dans le message ouvert
- [ ] Le surlignage est rendu sans injection : un extrait contenant du balisage s'affiche comme du texte (test dédié)
- [ ] **Scénario e2e** `E2E-SEARCH-010` v1 ajouté à `Api/Mail/e2e/scenarios.yml` : « Reconnaître un résultat et ouvrir
      le dossier du patient » — attendu : l'extrait surligne le terme cherché, et le patient désigné ouvre ses messages.
      Clients : angular requis, mobile requis avec **divergence temporaire** (raison : « la lecture enrichie arrive sur
      le mobile avec la refonte mobile », tache : task-451). Implémenté dans weda2, vu rouge par mutation
- [ ] `data-testid` sur chaque élément interactif ajouté (rangée Patients, chaque patient)
- [ ] Aucune chaîne en dur hors des conventions de libellés
- [ ] client-angular : code-only, aucun commit
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/angular.md` : un surlignage se construit à partir de
      positions et de texte échappé, jamais en injectant du HTML reçu

## Manual Test Plan

1. Lancer le backend sur le corpus fictif de task-438 : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de
   référence. Lancer weda2 : `cd Client/Angular/front && npm start`.
2. Rechercher `hemoglobine` : chaque résultat montre un extrait où « hémoglobine » est surligné, la mention « Document
   médical » ou « Corps », et son dossier d'origine.
3. Rechercher `bernard catherine` : la rangée « Patients » montre Catherine BERNARD, sa date de naissance et son nombre
   de messages, sans INS. Cliquer : la vue « Mails du patient » s'ouvre.
4. Rechercher `bernart` : aucune rangée Patients.
5. Ouvrir un résultat : les termes sont surlignés dans l'objet et le corps.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : jamais affichée ; seul le statut « INS qualifiée » est montré, pour que le médecin sache s'il peut se fier à
  l'identité. Les traits affichés sont ceux de l'identito-vigilance (nom de naissance, prénom, date de naissance, sexe)
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — la recherche est tracée côté serveur (`MailSearch`) ; l'ouverture de la vue « Mails du
  patient » est tracée comme aujourd'hui, au nom de la personne réelle, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable au client — aucune donnée stockée
- **AIPD / impact RGPD** : couvert par task-444 (affichage d'extraits)

## Branches

- `api-mail` (pushed) : feat/task-446-recherche-lire-un-resultat-extrait — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-446-recherche-lire-un-resultat-extrait
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS
